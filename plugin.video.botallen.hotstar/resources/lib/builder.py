# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from datetime import datetime
from codequick import Listitem, Script
from urlquick import MAX_AGE
import inputstreamhelper
from .contants import url_constructor, IMG_THUMB_H_URL, IMG_POSTER_V_URL, IMG_FANART_H_URL, MEDIA_TYPE
from .api import deep_get, HotstarAPI
from urllib import urlencode


class Builder:

    def __init__(self, refs):
        self.callbackRefs = {}
        for r in refs:
            self.callbackRefs[r.__name__] = r

    def buildMenu(self, menuItems):
        for each in menuItems:
            if not each.get("pageUri"):
                continue
            item = Listitem()
            item.label = each.get("name")
            item.art['fanart'] = "https://secure-media.hotstar.com/static/firetv/v1/poster_%s_in.jpg" % each.get(
                "name").lower() if not each.get("name").lower() == "genres" else "https://secure-media.hotstar.com/static/firetv/v1/poster_genre_in.jpg"
            item.set_callback(self.callbackRefs.get("menu_list") if each.get("pageType") else self.callbackRefs.get(
                "tray_list"), url=each.get("pageUri").replace("offset=0&size=20&tao=0&tas=5", "offset=0&size=100&tao=0&tas=15"))
            item.art.local_thumb(each.get("name").lower() + ".png")
            yield item

    def buildSearch(self, callback):
        return Listitem().search(**{
            "art": {
                "fanart": "https://secure-media.hotstar.com/static/firetv/v1/poster_search_in.jpg"
            },
            "callback": callback,  # self.callbackRefs.get("tray_list"),
            "params": {"url": ""}
        })

    def buildPage(self, items, nextPageUrl=None):
        for each in items:
            if not each.get("traySource") or each.get("traySource") == "THIRD_PARTY" or each.get("traySource") == "GRAVITY":
                continue
            art = info = None
            aItems = deep_get(each, "assets.items")
            if aItems:
                info = {
                    "plot": "Contains : " + " | ".join([x.get("title") for x in aItems])
                }
                art = {
                    "thumb": IMG_THUMB_H_URL % deep_get(aItems[0] or {}, "images.h"),
                    "icon": IMG_THUMB_H_URL % deep_get(aItems[0], "images.h"),
                    "poster": IMG_POSTER_V_URL % deep_get(aItems[0] or {}, "images.v"),
                    "fanart": IMG_FANART_H_URL % deep_get(aItems[0] or {}, "images.h"),
                }
            yield Listitem().from_dict(**{
                "label": each.get("title"),
                "art": art,
                "info": info,
                "callback": self.callbackRefs.get("tray_list"),
                "properties": {
                    "IsPlayable": False
                },
                "params": {
                    "url": url_constructor("/o/v1/tray/e/%s/items?tao=0&tas=15" % each.get("id")),
                    # "url": url_constructor("/o/v1/multi/get/content?ids=") + ",".join([str(x.get("contentId")) for x in aItems]) if aItems else url_constructor("/o/v1/tray/e/%s/items?tao=0&tas=15" % each.get("id"))
                }
            })
        if nextPageUrl:
            yield Listitem().next_page(url=nextPageUrl)

    def buildTray(self, items, nextPageUrl=None):
        for eachItem in items:
            yield Listitem().from_dict(**self._buildItem(eachItem))
        if nextPageUrl:
            yield Listitem().next_page(url=nextPageUrl)

    def buildPlay(self, playbackUrl, licenceUrl=None, playbackProto="mpd", label="", drm=False):
        is_helper = inputstreamhelper.Helper("mpd", drm=drm)
        if is_helper.check_inputstream():
            stream_headers = HotstarAPI._getPlayHeaders()
            return Listitem().from_dict(**{
                "label": label,
                "callback": playbackUrl,
                "properties": {
                    "IsPlayable": True,
                    "inputstreamaddon": is_helper.inputstream_addon,
                    "inputstream.adaptive.manifest_type": playbackProto,
                    "inputstream.adaptive.license_type": drm,
                    "inputstream.adaptive.stream_headers": urlencode(stream_headers),
                    "inputstream.adaptive.license_key": licenceUrl and licenceUrl + '|%s&Content-Type=application/octet-stream|R{SSM}|' % urlencode(stream_headers)
                }
            })
        return False

    def _buildItem(self, item):

        if item.get("assetType") in ["CHANNEL", "GENRE", "GAME", "LANGUAGE", "SHOW", "SEASON"]:
            callback = self.callbackRefs.get("menu_list") if item.get("assetType") == "GAME" or item.get(
                "pageType") == "HERO_LANDING_PAGE" else self.callbackRefs.get("tray_list")
            params = {"url": url_constructor(
                "/o/v1/tray/g/2/items?eid=%d&etid=2&tao=0&tas=100" % item.get("id")) if item.get("assetType") == "SHOW" else item.get("uri")}
        else:
            callback = self.callbackRefs.get("play_vod")
            params = {
                "contentId": item.get("contentId"),
                "subtag": item.get("isSubTagged") and "subs-tag:Hotstar%s|" % item.get("labels")[0],
                "label": item.get("title"),
                "drm": "com.widevine.alpha" if item.get("encrypted") else False
            }

        return {
            "label": "Season %d (%d) " % (
                item.get("seasonNo"), item.get("episodeCnt")) if item.get("assetType") == "SEASON" else item.get("title"),
            "art": {
                "icon": IMG_THUMB_H_URL % deep_get(item, "images.h"),
                "thumb": IMG_THUMB_H_URL % deep_get(item, "images.h"),
                "fanart": IMG_FANART_H_URL % deep_get(item, "images.h"),
                "poster": IMG_POSTER_V_URL % deep_get(item, "images.v")
            },
            "info": {
                "genre": item.get("genre"),
                "year": item.get("year"),
                "episode": item.get("episodeCnt"),
                "season": item.get("seasonNo") or item.get("seasonCnt"),
                "mpaa": item.get("parentalRatingName"),
                "plot": item.get("description"),
                "title": item.get("title"),
                "sorttitle": item.get("shortTitle"),
                "duration": item.get("duration"),
                "studio": item.get("cpDisplayName"),
                "premiered": item.get("startDate") and datetime.fromtimestamp(item.get("startDate")).strftime("%Y-%m-%d"),
                "path": "",
                "trailer": "",
                "dateadded": item.get("startDate") and datetime.fromtimestamp(item.get("startDate")).strftime("%Y-%m-%d"),
                "mediatype": MEDIA_TYPE.get(item.get("assetType"))
            },
            "properties": {
                "IsPlayable": False
            },
            "stream": {
                "video_codec": "h264",
                "width": "1920",
                "height": "1080",
                "audio_codec": "aac"
            },
            "callback": callback,
            "params": params
        }
