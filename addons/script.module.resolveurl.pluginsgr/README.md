# script.module.resolveurl.pluginsgr

Greek Resolvers for SMR

1. Import SMR and the PluginsGR Extension to your addon.
2. Call the resolveurl from your addon to resolve the Greek hosts.

```python
import resolveurl, xbmc, xbmcvfs
gr_plugins_path = 'special://home/addons/script.module.resolveurl.pluginsgr/resources/plugins/'
if xbmcvfs.exists(xxx_plugins_path): resolveurl.add_plugin_dirs(xbmc.translatePath(gr_plugins_path))

url = resolveurl.resolve(url)
```
