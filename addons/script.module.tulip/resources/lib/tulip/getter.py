# -*- coding: utf-8 -*-

'''
    Tulip library
    Author Twilight0

    SPDX-License-Identifier: GPL-3.0-only
    See LICENSES/GPL-3.0-only for more information.
'''


import os.path
import urllib.request as urllib2
import time
import ssl
import shutil
import subprocess
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
try:
    import certifi
except ImportError:
    certifi = None
try:
    import m3u8
except ImportError:
    m3u8 = None
from useragents import get_ua
from tulip.utils import percent, url2name, iteritems
from tulip import kodi
from tulip.log import log
from urllib.parse import urlparse, parse_qsl, urljoin


def find_ffmpeg(custom_path=None):
    """
    Locates an ffmpeg executable.
    Checks `custom_path` first (if provided by consumer add-on),
    then falls back to system PATH. Returns the executable path or None.
    """
    if custom_path and os.path.isfile(custom_path) and os.access(custom_path, os.X_OK):
        return custom_path
    return shutil.which('ffmpeg')


def has_ffmpeg(custom_path=None):
    """Returns True if ffmpeg is available either via custom_path or system PATH."""
    return find_ffmpeg(custom_path) is not None


class DownloadCancelled(Exception):
    """Raised when user cancels the download via ProgressDialog."""
    pass


def _create_ssl_context():
    """Create a modern SSL context, prioritizing certifi bundle if available."""
    try:
        if certifi:
            return ssl.create_default_context(cafile=certifi.where())
        return ssl.create_default_context()
    except Exception:
        return None


def retriever(
        source, destination, user_agent=None, referer=None,
        reporthook=None, data=None, timeout=30, resume=True, **kwargs
):
    """
    Downloads `source` to `destination` file.
    Supports resuming partial downloads, SSL verification via certifi, timeouts,
    and progress reporting.
    """
    if user_agent is None:
        user_agent = get_ua()

    if referer is None:
        referer = '{0}://{1}/'.format(urlparse(source).scheme, urlparse(source).netloc)

    headers = {'User-Agent': user_agent, 'Accept': '*/*', 'Referer': referer}
    if kwargs:
        headers.update(kwargs)

    existing_bytes = 0
    if resume and os.path.exists(destination):
        existing_bytes = os.path.getsize(destination)
        if existing_bytes > 0:
            headers['Range'] = 'bytes={0}-'.format(existing_bytes)

    req = urllib2.Request(source, data=data, headers=headers)
    ssl_context = _create_ssl_context()
    urlopen_kwargs = {'timeout': timeout}
    if ssl_context is not None:
        urlopen_kwargs['context'] = ssl_context

    try:
        resp = urllib2.urlopen(req, **urlopen_kwargs)
    except urllib2.HTTPError as err:
        if err.code == 416 and existing_bytes > 0:
            # Range Not Satisfiable (file may already be fully downloaded)
            return True
        raise

    with resp:
        status_code = getattr(resp, 'status', getattr(resp, 'code', 200))
        content_range = resp.headers.get('Content-Range', '')

        # Check if server actually accepted the range request
        if existing_bytes > 0 and (status_code == 206 or 'bytes' in content_range):
            open_mode = 'ab'
            initial_downloaded = existing_bytes
            content_length = int(resp.headers.get('Content-Length', -1))
            filesize = existing_bytes + content_length if content_length >= 0 else -1
        else:
            open_mode = 'wb'
            initial_downloaded = 0
            existing_bytes = 0
            filesize = int(resp.headers.get('Content-Length', -1))

        blocksize = 65536  # 64 KB buffer for higher throughput
        total_downloaded = initial_downloaded

        if reporthook:
            reporthook(total_downloaded, blocksize, filesize)

        with open(destination, open_mode) as out_file:
            while True:
                chunk = resp.read(blocksize)
                if not chunk:
                    break
                out_file.write(chunk)
                total_downloaded += len(chunk)
                if reporthook:
                    reporthook(total_downloaded, blocksize, filesize)

    return True


def download_media(
        url, output_folder, filename=None, heading=kodi.name(),
        line1='Downloading...[CR]%.02f MB of %.02f MB[CR]Speed: %.02f Kb/s',
        timeout=30, resume=True,
        status_template=None, cancelled_label='Cancelled', failed_label='Failed'
):
    """
    Downloads media file to output_folder displaying a Kodi progress dialog.
    Cleans up partial files if cancelled and resume is False.
    All text labels and templates can be passed by the caller for i18n support.
    Returns destination path on success, or None on cancel/error.
    """
    with kodi.ProgressDialog(heading, line1=line1) as pd:

        user_agent = get_ua()

        if not os.path.exists(output_folder):
            os.makedirs(output_folder)

        clean_url = url.split('|')[0] if '|' in url else url
        if not filename:
            filename = url2name(clean_url)
        # Strip potential query params from filename if any
        if '?' in filename:
            filename = filename.split('?')[0]

        valid_exts = ('.mp4', '.mkv', '.flv', '.avi', '.mpg', '.m4v', '.ts', '.mov', '.wmv')
        if not any(filename.lower().endswith(ext) for ext in valid_exts):
            filename += '.mp4'

        destination = os.path.join(output_folder, filename)
        part_destination = destination + '.part' if resume else destination

        custom_headers = {}
        if '|' in url:
            stream_url, _, head = url.rpartition('|')
            custom_headers = dict(parse_qsl(head))
            user_agent = custom_headers.pop('User-Agent', user_agent)
            referer = custom_headers.pop('Referer', '{0}://{1}/'.format(urlparse(stream_url).scheme, urlparse(stream_url).netloc))
        else:
            stream_url = url
            referer = '{0}://{1}/'.format(urlparse(stream_url).scheme, urlparse(stream_url).netloc)

        start_time = time.time()
        start_bytes = os.path.getsize(part_destination) if (resume and os.path.exists(part_destination)) else 0

        try:
            retriever(
                stream_url, part_destination, user_agent=user_agent, referer=referer,
                timeout=timeout, resume=resume,
                reporthook=lambda downloaded, blocksize, filesize: _pbhook(
                    downloaded, filesize, pd, start_time, start_bytes, line1,
                    status_template=status_template
                ),
                **custom_headers
            )
            # If we were downloading to .part, rename to final destination
            if part_destination != destination:
                if os.path.exists(destination):
                    os.remove(destination)
                os.rename(part_destination, destination)
            return destination

        except DownloadCancelled:
            pd.update(100, cancelled_label)
            if not resume and os.path.exists(destination):
                try:
                    os.remove(destination)
                except Exception:
                    pass
            return None

        except Exception as err:
            log('Download failed: {0}'.format(err))
            pd.update(100, failed_label)
            return None


def _pbhook(downloaded_bytes, filesize, pd, start_time, start_bytes, line1, status_template=None):
    """Calculates progress percentage, transfer speed, and ETA for the dialog."""
    elapsed = max(time.time() - start_time, 0.001)
    bytes_this_session = downloaded_bytes - start_bytes
    kbps_speed = (bytes_this_session / elapsed) / 1024 if bytes_this_session > 0 else 0

    downloaded_mb = float(downloaded_bytes) / (1024 * 1024)

    if filesize > 0:
        percent_val = int(min((float(downloaded_bytes) * 100.0 / filesize), 100))
        total_mb = float(filesize) / (1024 * 1024)
        eta_seconds = ((filesize - downloaded_bytes) / (kbps_speed * 1024)) if kbps_speed > 0 else 0
        status_line = line1 % (downloaded_mb, total_mb, kbps_speed)
        status_line += ' - ETA: %02d:%02d' % divmod(int(eta_seconds), 60)
    else:
        percent_val = 0
        if status_template:
            status_line = status_template.format(downloaded_mb=downloaded_mb, kbps_speed=kbps_speed)
        else:
            status_line = 'Downloading...[CR]%.02f MB[CR]Speed: %.02f Kb/s' % (downloaded_mb, kbps_speed)

    pd.update(percent_val, status_line)

    if pd.is_canceled():
        raise DownloadCancelled("User cancelled download")


class M3U8:

    def __init__(self, url, headers=None, heading=''):

        if m3u8 is None:
            raise ImportError("script.module.m3u8 is required to use M3U8")

        self.url = url
        self.headers = headers
        self.heading = heading

    def stream_picker(self, qualities, urls, heading=None):

        dialog_heading = heading or self.heading or 'Select a quality'
        _choice = kodi.selectDialog(heading=dialog_heading, list=qualities)

        if _choice is not None and 0 <= _choice < len(urls):
            self.url = urls[_choice]
            return self.url
        return None

    def m3u8_picker(self):

        headers = {}
        if '|' in self.url:
            link, _, head = self.url.rpartition('|')
            headers = dict(parse_qsl(head))
        elif self.headers:
            link = self.url
            headers = dict(self.headers)
        else:
            link = self.url

        if 'User-Agent' not in headers:
            headers['User-Agent'] = get_ua()

        try:
            parsed = m3u8.load(link, headers=headers)
            streams = parsed.playlists
        except Exception as err:
            log('Failed to load playlist for quality picking: {0}'.format(err))
            return self.url

        if not streams:
            return self.url

        # Sort streams by bandwidth/resolution descending so highest quality is listed first
        def _stream_sort_key(s):
            info = getattr(s, 'stream_info', None)
            if not info:
                return 0
            bw = getattr(info, 'bandwidth', 0) or getattr(info, 'average_bandwidth', 0) or 0
            res = getattr(info, 'resolution', None)
            res_val = (res[0] * res[1]) if (res and isinstance(res, (tuple, list)) and len(res) == 2) else 0
            return (bw, res_val)

        sorted_streams = sorted(streams, key=_stream_sort_key, reverse=True)

        qualities = []
        urls = []

        for stream in sorted_streams:
            info = getattr(stream, 'stream_info', None)
            label = ''
            if info and getattr(info, 'resolution', None):
                w, h = info.resolution
                label = '{0}x{1} ({2}p)'.format(w, h, h) if h else '{0}x{1}'.format(w, h)

            bw = (getattr(info, 'bandwidth', None) or getattr(info, 'average_bandwidth', None)) if info else None
            if bw:
                bw_val = int(bw)
                bw_str = '{0:.1f} Mbps'.format(bw_val / 1000000.0) if bw_val >= 1000000 else '{0} Kbps'.format(int(bw_val / 1000))
                label = '{0} @ {1}'.format(label, bw_str) if label else bw_str

            if not label:
                label = 'Auto'

            uri = getattr(stream, 'absolute_uri', None) or urljoin(parsed.base_uri or link, stream.uri)

            qualities.append(label)

            if '|' in self.url:
                urls.append(uri + ''.join(self.url.rpartition('|')[1:]))
            else:
                urls.append(uri)

        if len(qualities) == 1:
            self.url = urls[0]
            return self.url
        else:
            return self.stream_picker(qualities, urls)

    def downloader(
            self, output_folder, filename=None, heading='', line1='',
            pd_dialog='Downloading segment {0} from {1}',
            ffmpeg_path=None, prefer_ffmpeg=True, concurrency=5,
            timeout=30, resume=True,
            ffmpeg_status_template=None,
            live_status_template=None,
            init_segment_label=None
    ):
        """
        Downloads HLS stream to `output_folder`.
        All UI headings, status labels, and formatting templates can be passed
        by the calling add-on for localization (i18n).

        :param output_folder: Target directory.
        :param filename: Optional target filename. If omitted, derived from playlist URL.
        :param heading: Title for Kodi ProgressDialog.
        :param line1: Subtitle/status for ProgressDialog.
        :param pd_dialog: Format template for segment progress dialog.
        :param ffmpeg_path: Optional explicit path to ffmpeg executable (e.g. provided by consumer add-on).
        :param prefer_ffmpeg: If True and ffmpeg is found, delegates to ffmpeg lossless copy.
                              If False or ffmpeg is absent, uses the pure-Python segment downloader.
        :param concurrency: Number of worker threads for parallel segment downloads in pure-Python mode.
        :param timeout: Network socket timeout in seconds.
        :param resume: If True, uses a .part destination during download.
        :param ffmpeg_status_template: Optional format template for ffmpeg progress (e.g. "Downloading... ({time_str})").
        :param live_status_template: Optional format template for live recording (e.g. "Recording live... ({time_str}) - {chunks} chunks").
        :param init_segment_label: Optional label for fetching initialization segment.
        :return: Destination file path on success, or None on cancel/error.
        """
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)

        if not heading:
            heading = 'Downloading HLS Stream'

        url = self.m3u8_picker()
        if not url:
            return None

        custom_headers = {}
        if '|' in url:
            stream_url, _, head = url.rpartition('|')
            custom_headers = dict(parse_qsl(head))
        elif self.headers:
            stream_url = url
            custom_headers = dict(self.headers)
        else:
            stream_url = url

        if 'User-Agent' not in custom_headers:
            custom_headers['User-Agent'] = get_ua()

        # Check if FFmpeg is available and requested
        resolved_ffmpeg = find_ffmpeg(ffmpeg_path) if prefer_ffmpeg else None

        # Load playlist to inspect segments and determine format / duration
        try:
            parsed = m3u8.load(stream_url, headers=custom_headers)
        except Exception as err:
            log('Failed to parse HLS playlist {0}: {1}'.format(stream_url, err))
            return None

        # If it's a master playlist with variants, pick the first or highest
        if parsed.is_variant:
            if parsed.playlists:
                stream_url = parsed.playlists[0].absolute_uri
                parsed = m3u8.load(stream_url, headers=custom_headers)
            else:
                log('Variant playlist has no streams.')
                return None

        # Check if stream is live (sliding window without #EXT-X-ENDLIST)
        is_live = not getattr(parsed, 'is_endlist', True)

        # Determine file extension based on engine and playlist attributes
        is_fmp4 = any(getattr(s, 'init_section', None) is not None for s in parsed.segments)
        default_ext = '.mp4' if (resolved_ffmpeg or is_fmp4) else '.ts'

        if not filename:
            parsed_path = urlparse(stream_url).path
            base_name = os.path.basename(parsed_path).rsplit('.', 1)[0] or 'stream'
            if is_live:
                base_name += time.strftime('_%Y%m%d_%H%M%S')
            filename = base_name + default_ext
        else:
            if not any(filename.lower().endswith(ext) for ext in ('.mp4', '.mkv', '.ts')):
                filename += default_ext

        destination = os.path.join(output_folder, filename)
        part_destination = destination + '.part' if resume else destination

        # Calculate estimated total duration if available (for VOD)
        total_duration = sum(s.duration for s in parsed.segments if s.duration) if not is_live else 0

        format_name = 'mp4' if destination.lower().endswith('.mp4') else ('matroska' if destination.lower().endswith('.mkv') else 'mpegts')

        with kodi.ProgressDialog(heading=heading, line1=line1) as pd:
            if resolved_ffmpeg:
                log('Delegating HLS {0} to FFmpeg: {1}'.format('live recording' if is_live else 'download', resolved_ffmpeg))
                success = _ffmpeg_download(
                    stream_url=stream_url,
                    destination=part_destination,
                    ffmpeg_bin=resolved_ffmpeg,
                    headers=custom_headers,
                    pd=pd,
                    format_name=format_name,
                    total_duration=total_duration,
                    is_live=is_live,
                    status_template=ffmpeg_status_template,
                    live_status_template=live_status_template,
                    line1=line1
                )
            else:
                log('Using pure-Python HLS engine (is_live={0}, concurrency={1})'.format(is_live, concurrency))
                success = _python_hls_download(
                    playlist=parsed,
                    playlist_url=stream_url,
                    destination=part_destination,
                    headers=custom_headers,
                    pd=pd,
                    is_live=is_live,
                    concurrency=concurrency,
                    timeout=timeout,
                    pd_dialog=pd_dialog,
                    live_status_template=live_status_template,
                    init_segment_label=init_segment_label
                )

            if success:
                if part_destination != destination:
                    if os.path.exists(destination):
                        os.remove(destination)
                    os.rename(part_destination, destination)
                return destination
            else:
                # If user cancelled a live recording, preserve the recorded file if resume is True or it contains data
                if is_live and os.path.exists(part_destination) and os.path.getsize(part_destination) > 0:
                    if part_destination != destination:
                        if os.path.exists(destination):
                            os.remove(destination)
                        os.rename(part_destination, destination)
                    log('Live recording saved to {0}'.format(destination))
                    return destination

                if os.path.exists(part_destination) and not resume:
                    try:
                        os.remove(part_destination)
                    except Exception:
                        pass
                return None


def _ffmpeg_download(
        stream_url, destination, ffmpeg_bin, headers, pd, format_name=None,
        total_duration=0, is_live=False, status_template=None,
        live_status_template=None, line1=''
):
    """Executes ffmpeg subprocess to copy stream losslessly with progress tracking."""
    header_str = ''.join('{0}: {1}\r\n'.format(k, v) for k, v in iteritems(headers))

    cmd = [
        ffmpeg_bin,
        '-y',
        '-headers', header_str,
        '-i', stream_url,
        '-c', 'copy',
        '-bsf:a', 'aac_adtstoasc'
    ]

    if format_name:
        cmd.extend(['-f', format_name])

    cmd.append(destination)

    time_regex = re.compile(r'time=(\d{2}):(\d{2}):(\d{2}(?:\.\d+)?)')

    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            bufsize=1
        )
    except Exception as err:
        log('Failed to spawn ffmpeg: {0}'.format(err))
        return False

    try:
        last_stderr = []
        while proc.poll() is None:
            if pd.is_canceled():
                proc.terminate()
                try:
                    proc.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    proc.kill()
                return False

            line = proc.stderr.readline() if proc.stderr else ''
            if line:
                if len(last_stderr) >= 20:
                    last_stderr.pop(0)
                last_stderr.append(line.strip())
                match = time_regex.search(line)
                if match:
                    hours, mins, secs = match.groups()
                    current_seconds = float(hours) * 3600 + float(mins) * 60 + float(secs)
                    time_str = '{0:02d}:{1:02d}:{2:02d}'.format(int(hours), int(mins), int(float(secs)))
                    if is_live:
                        if live_status_template:
                            status = live_status_template.format(time_str=time_str, elapsed_seconds=current_seconds)
                        else:
                            status = 'Recording live stream... ({0})'.format(time_str)
                        pd.update(0, status)
                    else:
                        if total_duration > 0:
                            prog_percent = int(min((current_seconds / total_duration) * 100.0, 100))
                        else:
                            prog_percent = 0
                        if status_template:
                            status = status_template.format(time_str=time_str, percent=prog_percent)
                        else:
                            status = 'Downloading via FFmpeg... ({0})'.format(time_str)
                        pd.update(prog_percent, status)

        if proc.returncode != 0:
            log('FFmpeg failed with exit code {0}: {1}'.format(proc.returncode, ' | '.join(last_stderr[-5:])))
        return proc.returncode == 0

    except Exception as err:
        log('Error during FFmpeg execution: {0}'.format(err))
        if proc.poll() is None:
            proc.kill()
        return False


def _python_hls_download(
        playlist, playlist_url, destination, headers, pd, is_live=False,
        concurrency=5, timeout=30, pd_dialog='',
        live_status_template=None, init_segment_label=None
):
    """
    Pure-Python segment downloader supporting fMP4 init sections.
    Handles static VOD playlists via concurrent batches, and live sliding-window streams via polling.
    """
    ssl_ctx = _create_ssl_context()

    def _fetch_url(url):
        req = urllib2.Request(url, headers=headers)
        if ssl_ctx:
            with urllib2.urlopen(req, context=ssl_ctx, timeout=timeout) as resp:
                return resp.read()
        else:
            with urllib2.urlopen(req, timeout=timeout) as resp:
                return resp.read()

    try:
        with open(destination, 'ab' if is_live else 'wb') as out_f:
            base_uri = playlist.base_uri or playlist_url

            # Check for fMP4 initialization segment (#EXT-X-MAP)
            first_seg = playlist.segments[0] if playlist.segments else None
            if first_seg and getattr(first_seg, 'init_section', None):
                init_sec = first_seg.init_section
                init_uri = getattr(init_sec, 'absolute_uri', None) or urljoin(base_uri, init_sec.uri)
                init_msg = init_segment_label or 'Fetching initialization segment...'
                pd.update(0, init_msg)
                out_f.write(_fetch_url(init_uri))

            if is_live:
                # Continuous live recording loop
                seen_segments = set()
                start_rec_time = time.time()
                current_playlist = playlist

                while not pd.is_canceled():
                    base_uri = current_playlist.base_uri or playlist_url
                    new_segments = []

                    for seg in current_playlist.segments:
                        seg_uri = getattr(seg, 'absolute_uri', None) or urljoin(base_uri, seg.uri)
                        if seg_uri not in seen_segments:
                            seen_segments.add(seg_uri)
                            new_segments.append(seg_uri)

                    # Download any newly appeared segments
                    for seg_url in new_segments:
                        if pd.is_canceled():
                            break
                        chunk_data = _fetch_url(seg_url)
                        out_f.write(chunk_data)
                        out_f.flush()

                    elapsed = int(time.time() - start_rec_time)
                    h, rem = divmod(elapsed, 3600)
                    m, s = divmod(rem, 60)
                    time_str = '{0:02d}:{1:02d}:{2:02d}'.format(h, m, s)
                    if live_status_template:
                        status_line = live_status_template.format(time_str=time_str, chunks=len(seen_segments))
                    else:
                        status_line = 'Recording live stream... ({0}) - {1} chunks'.format(time_str, len(seen_segments))
                    pd.update(0, status_line)

                    if pd.is_canceled():
                        break

                    # Check if stream ended naturally
                    if getattr(current_playlist, 'is_endlist', False):
                        log('Live stream ended (#EXT-X-ENDLIST reached).')
                        return True

                    # Sleep for half the target duration before re-fetching playlist
                    target_duration = getattr(current_playlist, 'target_duration', 6) or 6
                    sleep_interval = max(float(target_duration) / 2.0, 1.0)
                    time.sleep(sleep_interval)

                    try:
                        current_playlist = m3u8.load(playlist_url, headers=headers)
                    except Exception as poll_err:
                        log('Warning: failed to refresh live playlist: {0}'.format(poll_err))

                return True

            else:
                # VOD Static Playlist Mode
                segments = playlist.segments
                total_segments = len(segments)

                if total_segments == 0:
                    log('Playlist contains 0 segments.')
                    return False

                resolved_segments = [
                    getattr(s, 'absolute_uri', None) or urljoin(base_uri, s.uri)
                    for s in segments
                ]

                # Parallel download of chunks maintaining index order
                with ThreadPoolExecutor(max_workers=max(1, concurrency)) as executor:
                    batch_size = max(1, concurrency * 2)
                    downloaded_count = 0

                    for i in range(0, total_segments, batch_size):
                        if pd.is_canceled():
                            return False

                        chunk_slice = resolved_segments[i:i + batch_size]
                        future_to_idx = {
                            executor.submit(_fetch_url, seg_url): idx
                            for idx, seg_url in enumerate(chunk_slice, start=i)
                        }

                        results = {}
                        for future in as_completed(future_to_idx):
                            if pd.is_canceled():
                                return False
                            idx = future_to_idx[future]
                            results[idx] = future.result()

                        # Write chunks to disk in sequential order
                        for idx in sorted(results.keys()):
                            out_f.write(results[idx])
                            downloaded_count += 1
                            pct = int((downloaded_count * 100.0) / total_segments)
                            status_line = pd_dialog.format(downloaded_count, total_segments) if pd_dialog else 'Segment {0}/{1}'.format(downloaded_count, total_segments)
                            pd.update(pct, status_line)

                return True

    except Exception as err:
        log('Pure-Python HLS download failed: {0}'.format(err))
        return False





