import sys
import requests
import xbmcgui
import xbmcplugin
import xbmcaddon

addon = xbmcaddon.Addon("plugin.video.gronkhtvarchive")
months = [addon.getLocalizedString(30009),
                  addon.getLocalizedString(30010),
                  addon.getLocalizedString(30011),
                  addon.getLocalizedString(30012),
                  addon.getLocalizedString(30013),
                  addon.getLocalizedString(30014),
                  addon.getLocalizedString(30015),
                  addon.getLocalizedString(30016),
                  addon.getLocalizedString(30017),
                  addon.getLocalizedString(30018),
                  addon.getLocalizedString(30019),
                  addon.getLocalizedString(30020)
          ]
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
def get_streams(page=None, tag_id=None):
    streams = {}
    counter = 0

    if page is None:
        while True:
            add_streams = stream_request(offset=counter, tag_id=tag_id)
            if add_streams is None:
                break
            streams.update(add_streams)
            counter += 1
        return streams
    else:
        return stream_request(offset=page, tag_id=tag_id)


def stream_request(offset=None, tag_id=None):
    params = {"sort": "date", "direction": "desc"}
    streams = {}
    if tag_id:
        params["tags"] = tag_id
    params.update({"offset": offset * 25, "first": 25})
    r = requests.get(SEARCH_API, params=params)
    try:
        vids = r.json()["results"]["videos"]
        for vid in vids:
            tags = [tag["title"] for tag in vid["tags"]]
            streams[vid["episode"]] = {"title": vid["title"],
                                       "length": vid["video_length"],
                                       "created_at": vid["created_at"][:10],
                                       "thumbnail": vid["preview_url"],
                                       "tags": tags
                                       }
    except KeyError:
        return None
    return streams


def get_stream_title(stream_dict, episode):
    split_title = stream_dict[episode]["title"].split(" - ", 1)
    if len(split_title) > 1:
        return split_title[1]
    else:
        return split_title[0]


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
    vid_links[addon.getLocalizedString(30024)] = playlist_url

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
    return None


# Search functions
def search_for_title(page=0, option="None"):
    page = int(page)
    xbmcplugin.setPluginCategory(__handle__, addon.getLocalizedString(30002))
    xbmcplugin.setContent(__handle__, 'videos')
    if option == "None":
        key_input = get_keyboard_input()
    else:
        key_input = option
    if key_input:
        streams = get_streams()
        found_streams = []
        for episode, info in streams.items():
            if key_input in info["title"].lower():
                found_streams.append(episode)
        create_streamlist(streams, sorted(found_streams, reverse=True), "Titel", page, option=key_input)


def search_for_month(page=0, option="None"):
    page = int(page)
    xbmcplugin.setPluginCategory(__handle__, addon.getLocalizedString(30003))
    xbmcplugin.setContent(__handle__, 'videos')
    if option == "None":
        month = get_month_from_id(xbmcgui.Dialog().select(addon.getLocalizedString(30008), months))
    else:
        month = option
    if month != -1:
        all_streams = get_streams()
        found_streams = []
        for episode, info in all_streams.items():
            if month == get_created_month(info["created_at"]):
                found_streams.append(episode)
        create_streamlist(all_streams, sorted(found_streams, reverse=True), "Monat", page, option=month)


def search_for_category_list(page=0, option="None"):
    page = int(page)
    xbmcplugin.setPluginCategory(__handle__, addon.getLocalizedString(30006))
    xbmcplugin.setContent(__handle__, 'videos')
    tag_id = ""
    if option == "None":
        all_tags = get_all_tags()
        categories = sorted(list(all_tags.values()))
        category = xbmcgui.Dialog().select(addon.getLocalizedString(30021), categories)
        if category != -1:
            category = categories[category]
            tag_id = get_tag_id(all_tags, category)
    else:
        tag_id = option
    if tag_id:
        all_streams = get_streams(tag_id=tag_id)
        create_streamlist(all_streams, sorted(all_streams, reverse=True), "Kategorie (Liste)", page, option=tag_id)


def search_for_category_freetext(page=0, option="None"):
    page = int(page)
    xbmcplugin.setPluginCategory(__handle__, addon.getLocalizedString(30007))
    xbmcplugin.setContent(__handle__, 'videos')
    tag_id = ""
    if option == "None":
        key_input = get_keyboard_input()
        if key_input:
            all_tags = get_all_tags()
            tag_id = get_tag_id(all_tags, key_input)
    else:
        tag_id = option
    if tag_id:
        all_streams = get_streams(tag_id=tag_id)
        create_streamlist(all_streams, sorted(all_streams, reverse=True), "Kategorie (Freitext)", page,
                          option=tag_id)


def search_for_year(page=0, option="None"):
    page = int(page)
    xbmcplugin.setPluginCategory(__handle__, addon.getLocalizedString(30004))
    xbmcplugin.setContent(__handle__, 'videos')
    if option == "None":
        key_input = get_keyboard_input()
        if key_input:
            if key_input.isdecimal():
                all_streams = get_streams()
                found_streams = []
                for episode, info in all_streams.items():
                    if key_input == get_created_year(info["created_at"]):
                        found_streams.append(episode)
                create_streamlist(all_streams, sorted(found_streams, reverse=True), "Jahr", page, key_input)
    else:
        key_input = option
        all_streams = get_streams()
        found_streams = []
        for episode, info in all_streams.items():
            if key_input == get_created_year(info["created_at"]):
                found_streams.append(episode)
        create_streamlist(all_streams, sorted(found_streams, reverse=True), "Jahr", page, key_input)


def search_for_month_year(page=0, option="None"):
    page = int(page)
    xbmcplugin.setPluginCategory(__handle__, addon.getLocalizedString(30005))
    xbmcplugin.setContent(__handle__, 'videos')

    if option == "None":
        month = get_month_from_id(xbmcgui.Dialog().select(addon.getLocalizedString(30008), months))
    else:
        month = option.split("-")[0]

    if month != -1:
        if option == "None":
            key_input = get_keyboard_input()
            if key_input:
                if key_input.isdecimal():
                    all_streams = get_streams()
                    found_streams = []
                    for episode, info in all_streams.items():
                        if key_input == get_created_year(info["created_at"]) and month == get_created_month(
                                info["created_at"]):
                            found_streams.append(episode)
                    create_streamlist(all_streams, sorted(found_streams, reverse=True), "Monat + Jahr", page,
                                      option="-".join([month, key_input]))
        else:
            key_input = option.split("-")[1]
            all_streams = get_streams()
            found_streams = []
            for episode, info in all_streams.items():
                if key_input == get_created_year(info["created_at"]) and month == get_created_month(
                        info["created_at"]):
                    found_streams.append(episode)
            create_streamlist(all_streams, sorted(found_streams, reverse=True), "Monat + Jahr", page,
                              option="-".join([month, key_input]))


# Build UI
def main_menu():
    xbmcplugin.setPluginCategory(__handle__, '')
    xbmcplugin.setContent(__handle__, 'videos')
    items = [addon.getLocalizedString(30000), addon.getLocalizedString(30001)]
    for item in items:
        list_item = xbmcgui.ListItem(label=item)
        url = get_url(action='listing', category=item, page=0)
        is_folder = True
        xbmcplugin.addDirectoryItem(__handle__, url, list_item, is_folder)
    xbmcplugin.addSortMethod(__handle__, xbmcplugin.SORT_METHOD_NONE)
    xbmcplugin.endOfDirectory(__handle__)


def all_streams_menu(page=0):
    page = int(page)
    xbmcplugin.setPluginCategory(__handle__, addon.getLocalizedString(30000))
    xbmcplugin.setContent(__handle__, 'videos')
    all_streams = get_streams(page=page)
    sorted_episodes = sorted(all_streams.keys(), reverse=True)
    create_streamlist(all_streams, sorted_episodes, "Vergangene Streams", page, shortlist=True)


def search_menu():
    xbmcplugin.setPluginCategory(__handle__, addon.getLocalizedString(30001))
    xbmcplugin.setContent(__handle__, 'videos')
    items = [
        addon.getLocalizedString(30002),
        addon.getLocalizedString(30003),
        addon.getLocalizedString(30004),
        addon.getLocalizedString(30005),
        addon.getLocalizedString(30006),
        addon.getLocalizedString(30007)
    ]
    for item in items:
        list_item = xbmcgui.ListItem(label=item)
        url = get_url(action='listing', category=item, page=0, option="None")
        is_folder = True
        xbmcplugin.addDirectoryItem(__handle__, url, list_item, is_folder)
    xbmcplugin.addSortMethod(__handle__, xbmcplugin.SORT_METHOD_NONE)
    xbmcplugin.endOfDirectory(__handle__)


# Helper functions
def create_streamlist(all_streams_dict, streams_order, category, page=0, option=None, shortlist=False):
    stream_list = []
    if shortlist:
        stream_counter = 0 + 25 * page
    else:
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
            url = get_url(action='play', video=episode)
            is_folder = False
            stream_list.append((url, list_item, is_folder))

        stream_counter += 1

    if len(stream_list) == 25:
        if option:
            url = get_url(action="listing", category=category, page=str(page + 1), option=option)
        else:
            url = get_url(action="listing", category=category, page=str(page + 1))
        list_item = xbmcgui.ListItem(label="...")
        is_folder = True
        stream_list.append((url, list_item, is_folder))

    xbmcplugin.addDirectoryItems(__handle__, stream_list)
    xbmcplugin.addSortMethod(__handle__, xbmcplugin.SORT_METHOD_NONE)
    xbmcplugin.endOfDirectory(__handle__)


def play_video(episode):
    path = get_vid_links(episode)
    quality = addon.getSetting("quality")
    quality_err_text = addon.getLocalizedString(30026)

    sort_key = {
        addon.getLocalizedString(30024): 0,
        addon.getLocalizedString(30029): 1,
        addon.getLocalizedString(30030): 2,
        addon.getLocalizedString(30031): 3
    }

    if quality == "0":
        chosen_quality = sort_key[addon.getLocalizedString(30024)]
    elif quality == "1":
        if "1080p60" in path.keys():
            chosen_quality = list(path.keys()).index("1080p60")
        else:
            dialog = xbmcgui.Dialog()
            dialog.ok(addon.getLocalizedString(30027), quality_err_text)
            if "720p" in path.keys():
                chosen_quality = list(path.keys()).index("720p")
            else:
                chosen_quality = list(path.keys()).index("360p")
    elif quality == "2":
        if "720p" in path.keys():
            chosen_quality = list(path.keys()).index("720p")
        else:
            dialog = xbmcgui.Dialog()
            dialog.ok(addon.getLocalizedString(30027), quality_err_text)
            chosen_quality = list(path.keys()).index("360p")
    elif quality == "3":
        chosen_quality = list(path.keys()).index("360p")
    else:
        chosen_quality = xbmcgui.Dialog().select(addon.getLocalizedString(30028), sorted(path.keys(), key=lambda i: sort_key[i]))

    if chosen_quality != -1:
        play_item = xbmcgui.ListItem(path=path[list(path.keys())[chosen_quality]])
        xbmcplugin.setResolvedUrl(__handle__, True, listitem=play_item)


def router(paramstring):
    params = dict(parse_qsl(paramstring))
    if params:
        if params['action'] == 'listing':
            if params["category"] == addon.getLocalizedString(30000):
                all_streams_menu(params["page"])
            elif params["category"] == addon.getLocalizedString(30001):
                search_menu()
            elif params["category"] == addon.getLocalizedString(30002):
                search_for_title(params["page"], params["option"])
            elif params["category"] == addon.getLocalizedString(30003):
                search_for_month(params["page"], params["option"])
            elif params["category"] == addon.getLocalizedString(30004):
                search_for_year(params["page"], params["option"])
            elif params["category"] == addon.getLocalizedString(30005):
                search_for_month_year(params["page"], params["option"])
            elif params["category"] == addon.getLocalizedString(30006):
                search_for_category_list(params["page"], params["option"])
            elif params["category"] == addon.getLocalizedString(30007):
                search_for_category_freetext(params["page"], params["option"])
        elif params['action'] == 'play':
            play_video(params['video'])
        else:
            raise ValueError('Invalid paramstring: {}!'.format(paramstring))
    else:
        main_menu()


if __name__ == "__main__":
    router(sys.argv[2][1:])
