COLOR_MAP = {
    "STRMCNTR": "aqua",
    "FAWA": "orange",
    "FUTBOLX": "green",
    "MP66": "purple",
    "STRMXHD": "blue",
    "STRMGATE": "cyan",
    "SPRTSPASS": "pink",
    "SPORTS": "yellow",
    "ISTRMEAST": "lime",
    "720p": "gray",
    "1080p": "black",
    "ABC": "white"
}

DEFAULT_COLOR = "red"

# Channels whose source word maps to DEFAULT_COLOR are hidden from the list.
HIDE_DEFAULT_COLOR = True

# Domains whose streams should never appear in the list.
# Matched against the channel URL host and, for worker/MAC channels, the portal host.
# Subdomains match too (e.g. "medcom.id" matches "edge.medcom.id").
EXCLUDE_DOMAINS = [
    "edge.medcom.id",
]
