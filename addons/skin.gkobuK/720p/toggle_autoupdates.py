import xbmc, json
query = '{"jsonrpc":"2.0", "method":"Settings.GetSettingValue","params":{"setting":"general.addonupdates"}, "id":1}'
response = xbmc.executeJSONRPC(query)
response_result = json.loads(response)
if response_result['result']['value'] == 0:
    xbmc.executeJSONRPC('{"jsonrpc":"2.0","method":"Settings.SetSettingValue","id":1,"params":{"setting":"general.addonupdates","value":2}}')
elif response_result['result']['value'] == 2:
    xbmc.executeJSONRPC('{"jsonrpc":"2.0","method":"Settings.SetSettingValue","id":1,"params":{"setting":"general.addonupdates","value":1}}')
else:
    pass
    