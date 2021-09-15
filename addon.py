import sys
import requests
import xbmcgui
import xbmcplugin

python_version = sys.version_info[0]
if python_version == 2:
    from urllib import urlencode
    from urlparse import parse_qsl
else:
    from urllib.parse import urlencode, parse_qsl

ALL_TAGS_API = "https://api.gronkh.tv/v1/tags/all"
SEARCH_API = "https://api.gronkh.tv/v1/search"
PLAYLIST_API = "https://api.gronkh.tv/v1/video/playlist"

__url__ = sys.argv[0]
__handle__ = int(sys.argv[1])


# Getter functions
def get_all_streams():
    all_vids = {}
    counter = 0
    while True:
        r = requests.get(SEARCH_API, params={"offset": counter * 25, "first": 25})
        try:
            vids = r.json()["results"]["videos"]
            for vid in vids:
                tags = [tag["title"] for tag in vid["tags"]]
                all_vids[vid["episode"]] = {"title": vid["title"],
                                            "length": vid["video_length"],
                                            "created_at": vid["created_at"][:10],
                                            "thumbnail": vid["preview_url"],
                                            "tags": tags
                                            }
            counter += 1
        except KeyError:
            break
    return all_vids


def get_streams(search_string=None, tags=None):
    all_vids = {}
    params = {}
    page = 0
    if search_string:
        params["query"] = search_string
    if tags:
        params["tags"] = ",".join(tags)
    while True:
        params.update({"offset": page * 25, "first": 25})
        r = requests.get(SEARCH_API, params=params)
        try:
            vids = r.json()["results"]["videos"]
            for vid in vids:
                tags = [tag["title"] for tag in vid["tags"]]
                all_vids[vid["episode"]] = {"title": vid["title"],
                                            "length": vid["video_length"],
                                            "created_at": vid["created_at"][:10],
                                            "thumbnail": vid["preview_url"],
                                            "tags": tags
                                            }
            page += 1
        except KeyError:
            break
    return all_vids


def get_stream_title(stream_dict, episode):
    return stream_dict[episode]["title"].split(" - ", 1)[1]


def get_all_tags():
    r = requests.get(ALL_TAGS_API)
    if r.status_code == 200:
        if python_version == 2:
            return {unicode(item['id']): unicode(item['title']) for item in r.json()}
        else:
            return {item['id']: item['title'] for item in r.json()}


def get_keyboard_input():
    key_input = None
    keyboard = xbmc.Keyboard()
    keyboard.doModal()
    if keyboard.isConfirmed():
        if python_version == 2:
            key_input = unicode(keyboard.getText()).lower()
        else:
            key_input = keyboard.getText().lower()
    return key_input


def get_vid_links(episode):
    vid_links = {}
    r = requests.get(PLAYLIST_API, params={"episode": episode})
    playlist_url = r.json()["playlist_url"]

    data = requests.get(playlist_url).text
    resolution = ""
    for line in data.split("\n"):
        if line.startswith("#EXT-X-STREAM-INF:") or line.startswith("https"):
            if line.startswith("#EXT-X-STREAM-INF:"):
                resolution = line.split(":")[1].split(",")[-1].split("=")[1].replace('"', "").strip()
                continue
            else:
                vid_links[resolution] = line.strip()
    vid_links["Adaptive"] = playlist_url

    return vid_links


def get_url(**kwargs):
    return '{}?{}'.format(__url__, urlencode(kwargs))


def get_created_month(created_at):
    return created_at[5:7]


def get_created_year(created_at):
    return created_at[:4]


def get_month_from_id(month_id):
    if month_id == -1:
        return -1
    month = month_id + 1
    month = "0" + str(month) if month < 10 else str(month)
    return month


def get_tag_id(all_tags, tag):
    for key, value in all_tags.items():
        if tag.lower() == value.lower():
            return key


# Search functions
def search_for_title():
    xbmcplugin.setPluginCategory(__handle__, "Titelsuche")
    xbmcplugin.setContent(__handle__, 'videos')
    key_input = get_keyboard_input()
    if key_input:
        streams = get_streams(key_input)
        create_streamlist(streams, sorted(list(streams.keys()), reverse=True))


def search_for_month():
    xbmcplugin.setPluginCategory(__handle__, "Monatssuche")
    xbmcplugin.setContent(__handle__, 'videos')
    months = ["Januar", "Februar", "Maerz", "April", "Mai", "Juni", "Juli", "August", "September", "Oktober",
              "November", "Dezember"]
    month = get_month_from_id(xbmcgui.Dialog().select("Monat auswaehlen", months))
    if month != -1:
        all_streams = get_streams()
        found_streams = []
        for episode, info in all_streams.items():
            if month == get_created_month(info["created_at"]):
                found_streams.append(episode)
        create_streamlist(all_streams, sorted(found_streams, reverse=True))


def search_for_category_list():
    xbmcplugin.setPluginCategory(__handle__, "Kategoriesuche (Liste)")
    xbmcplugin.setContent(__handle__, 'videos')
    all_tags = get_all_tags()
    categories = sorted(list(all_tags.values()))
    category = xbmcgui.Dialog().select("Kategorie auswaehlen", categories)
    if category != -1:
        category = categories[category]
        tag_id = get_tag_id(all_tags, category)
        all_streams = get_streams(tags=[tag_id])
        create_streamlist(all_streams, sorted(all_streams, reverse=True))


def search_for_category_freetext():
    xbmcplugin.setPluginCategory(__handle__, "Kategoriesuche (Freitext)")
    xbmcplugin.setContent(__handle__, 'videos')
    key_input = get_keyboard_input()
    if key_input:
        all_tags = get_all_tags()
        tag_id = get_tag_id(all_tags, key_input)
        all_streams = get_streams(tags=[tag_id])
        create_streamlist(all_streams, sorted(all_streams, reverse=True))


def search_for_year():
    xbmcplugin.setPluginCategory(__handle__, "Jahressuche")
    xbmcplugin.setContent(__handle__, 'videos')
    key_input = get_keyboard_input()
    if key_input:
        if key_input.isdecimal():
            all_streams = get_streams()
            found_streams = []
            for episode, info in all_streams.items():
                if key_input == get_created_year(info["created_at"]):
                    found_streams.append(episode)
            create_streamlist(all_streams, sorted(found_streams, reverse=True))


def search_for_month_year():
    xbmcplugin.setPluginCategory(__handle__, "Monats- & Jahressuche")
    xbmcplugin.setContent(__handle__, 'videos')

    monate = ["Januar", "Februar", "Maerz", "April", "Mai", "Juni", "Juli", "August", "September", "Oktober",
              "November", "Dezember"]
    month = get_month_from_id(xbmcgui.Dialog().select("Monat auswaehlen", monate))
    if month != -1:
        key_input = get_keyboard_input()
        if key_input:
            if key_input.isdecimal() and month != -1:
                all_streams = get_streams()
                found_streams = []
                for episode, info in all_streams.items():
                    if key_input == get_created_year(info["created_at"]) and month == get_created_month(
                            info["created_at"]):
                        found_streams.append(episode)
                create_streamlist(all_streams, sorted(found_streams, reverse=True))


# Build UI
def search_menu():
    xbmcplugin.setPluginCategory(__handle__, 'Suche')
    xbmcplugin.setContent(__handle__, 'videos')
    items = ["Titel", "Monat", "Jahr", "Monat + Jahr", "Kategorie (Liste)", "Kategorie (Freitext)"]
    for item in items:
        list_item = xbmcgui.ListItem(label=item)
        url = get_url(action='listing', category=item)
        is_folder = True
        xbmcplugin.addDirectoryItem(__handle__, url, list_item, is_folder)
    xbmcplugin.addSortMethod(__handle__, xbmcplugin.SORT_METHOD_NONE)
    xbmcplugin.endOfDirectory(__handle__)


def all_streams_menu(page=0):
    xbmcplugin.setPluginCategory(__handle__, "Vergangene Streams")
    xbmcplugin.setContent(__handle__, 'videos')
    all_streams = get_all_streams()
    sorted_episodes = sorted(all_streams.keys(), reverse=True)
    create_streamlist(all_streams, sorted_episodes, str(page))


def main_menu():
    xbmcplugin.setPluginCategory(__handle__, '')
    xbmcplugin.setContent(__handle__, 'videos')
    items = ["Vergangene Streams", "Streamsuche"]
    for item in items:
        list_item = xbmcgui.ListItem(label=item)
        url = get_url(action='listing', category=item, page=0)
        is_folder = True
        xbmcplugin.addDirectoryItem(__handle__, url, list_item, is_folder)
    xbmcplugin.addSortMethod(__handle__, xbmcplugin.SORT_METHOD_NONE)
    xbmcplugin.endOfDirectory(__handle__)


# Helper functions
def create_streamlist(all_streams_dict, streams_order, page="0"):
    page = int(page)
    stream_list = []
    stream_counter = 0
    for episode in streams_order:
        if page * 25 <= stream_counter < page * 25 + 25:
            title = get_stream_title(all_streams_dict, episode)
            list_item = xbmcgui.ListItem(label=title)
            list_item.setInfo('video', {'title': 'Stream ' + str(episode) + ": " + title,
                                        'episode': episode,
                                        'year': int(all_streams_dict[episode]["created_at"][:4]),
                                        'duration': int(all_streams_dict[episode]["length"]),
                                        'genre': 'Games',
                                        'mediatype': 'Video'})
            list_item.setArt(
                {'thumb': all_streams_dict[episode]['thumbnail'],
                 'icon': all_streams_dict[episode]['thumbnail'],
                 'fanart': all_streams_dict[episode]['thumbnail']})
            list_item.setProperty('IsPlayable', 'true')
            url = get_url(action='play', video=episode, page=page)
            is_folder = False
            stream_list.append((url, list_item, is_folder))

        stream_counter += 1

    if len(stream_list) == 25:
        url = get_url(action="listing", category="Vergangene Streams", page=str(page + 1))
        list_item = xbmcgui.ListItem(label="...")
        is_folder = True
        stream_list.append((url, list_item, is_folder))

    xbmcplugin.addDirectoryItems(__handle__, stream_list)
    xbmcplugin.addSortMethod(__handle__, xbmcplugin.SORT_METHOD_NONE)
    xbmcplugin.endOfDirectory(__handle__)


def play_video(episode):
    path = get_vid_links(episode)
    sort_key = {"Adaptive": 0, "1080p60": 1, "720p": 2, "360p": 3}

    chosen_quality = xbmcgui.Dialog().select("Qualitaet auswaehlen", sorted(path.keys(), key=lambda i: sort_key[i]))
    if chosen_quality != -1:
        play_item = xbmcgui.ListItem(path=path[list(path.keys())[chosen_quality]])
        xbmcplugin.setResolvedUrl(__handle__, True, listitem=play_item)


def router(paramstring):
    params = dict(parse_qsl(paramstring))
    if params:
        if params['action'] == 'listing':
            if params["category"] == "Vergangene Streams":
                all_streams_menu(params["page"])
            elif params["category"] == "Streamsuche":
                search_menu()
            elif params["category"] == "Titel":
                search_for_title()
            elif params["category"] == "Monat":
                search_for_month()
            elif params["category"] == "Jahr":
                search_for_year()
            elif params["category"] == "Monat + Jahr":
                search_for_month_year()
            elif params["category"] == "Kategorie (Liste)":
                search_for_category_list()
            elif params["category"] == "Kategorie (Freitext)":
                search_for_category_freetext()
        elif params['action'] == 'play':
            play_video(params['video'])
        else:
            raise ValueError('Invalid paramstring: {}!'.format(paramstring))
    else:
        main_menu()


if __name__ == "__main__":
    router(sys.argv[2][1:])
