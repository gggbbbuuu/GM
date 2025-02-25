import xbmcgui

def link_dialog(links, return_idx=False, hide_links=True):
    if len(links) == 0:
        xbmcgui.Dialog().notification("Notice", "No links were found.", xbmcgui.NOTIFICATION_INFO)
        return None
    if len(links) == 1:
        link = links[0]
        if "(" in link and link.endswith(")"):
            split = link.split('(')
            link = split[0]
        return link if not return_idx else 0
    options = []
    for i, link in enumerate(links):
        if "(" in link and link.endswith(")"):
            split = link.split('(')
            label = split[-1].replace(')', '')
            options.append(label) if hide_links else options.append("%s - %s" % (label, split[0]))
            links[i] = split[0]
        else:
            options.append("Link " + str(i + 1)) if hide_links else options.append(link)
    idx = xbmcgui.Dialog().select("Choose a link", options)
    if idx == -1: return None
    return links[idx] if not return_idx else idx

def remove_name(link):
    if "(" in link and link.endswith(")"):
        return link.split("(")[0]
    else:
        return link
