RPC = {
    "application_id": "000000000000000000",  # REQUIRED - client ID from discord.com/developers/applications

    "large_image": "js",                 # OPTIONAL - asset key from Rich Presence > Art Assets
    "large_text": "providers.js",      # OPTIONAL - hover text on large image

    "small_image": "vscode-circle",                       # OPTIONAL - small corner image asset key, leave "" to disable
    "small_text": "",                        # OPTIONAL - hover text on small image, leave "" to disable

    "primary_text": "Visual Studio Code",               # REQUIRED - bold top line under the app name
    "secondary_text": "Idling in v3/player/providers.js",   # OPTIONAL - smaller second line, leave "" to disable

    "start_timestamp": True                  # OPTIONAL - True shows elapsed timer from startup
}
