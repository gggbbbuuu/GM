import threading
import ctypes
import threading
import time
import xbmcgui
from resources.lib.modules.log_utils import log
from resources.lib.modules import liveresolver, control
res = liveresolver.Liveresolver()

try:
   import queue
except ImportError:
   import Queue as queue


def getLinks(out):
	if control.setting('link_precheck') == 'true' or len(out) < int(control.setting('min_links')) :
		return out

	done = 0
	pDialog = xbmcgui.DialogProgress()
	pDialog.create('Streams', 'Searching for streams...')

	NUM_OF_THREADS = int(control.setting("threads_num"))
	TIMEOUT = int(control.setting("search_timeout"))

	threads = []
	input_queue = queue.Queue()
	output_queue = []

	for u in out:
		input_queue.put(u)

	for i in range(min(NUM_OF_THREADS, len(out))):
		t = Thread(input_queue, output_queue)
		threads.append(t)

	for t in threads:
		t.start()

	t_start = time.time()
	while True:
		
		msg = "Links processed: {} / {} - Working links: {}\n\nTime elapsed: {}s".format(len(output_queue), len(out), len(list(filter(None, output_queue))), int(round((time.time() - t_start))))
		percent = int(round((len(output_queue)/float(len(out)))*100))
		pDialog.update(percent, msg)
		if pDialog.iscanceled() or ((time.time() - t_start) > TIMEOUT) or int(round((len(output_queue)/float(len(out)))*100)) == 100:
			pDialog.update(100)
			pDialog.close()
			for t in threads:
				del t
			break
		time.sleep(0.5)

	return list(filter(None, output_queue))


class Thread(threading.Thread):
	def __init__(self, input_queue, output):
		self.input_queue = input_queue
		self.output = output
		threading.Thread.__init__(self)

	def run(self):
		try:
			while True:
				url = self.input_queue.get()
				resolved = res.resolve_search(url)
				if resolved:
					self.output.append(url)
				else:
					self.output.append(None)


		except Exception as e:
			self.output.append(None)