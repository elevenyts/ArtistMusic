#
# Copyright (C) 2021-2022 by TheAloneteam@Github, < https://github.com/TheAloneTeam >.
#
# This file is part of < https://github.com/TheAloneTeam/AloneMusic > project,
# and is released under the "GNU v3.0 License Agreement".
# Please see < https://github.com/TheAloneTeam/AloneMusic/blob/master/LICENSE >
#
# All rights reserved.

import os
import re

import aiofiles
import aiohttp
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont
from py_yt import VideosSearch

from config import YOUTUBE_IMG_URL


def changeImageSize(maxWidth, maxHeight, image):
    widthRatio = maxWidth / image.size[0]
    heightRatio = maxHeight / image.size[1]
    newWidth = int(widthRatio * image.size[0])
    newHeight = int(heightRatio * image.size[1])
    newImage = image.resize((newWidth, newHeight))
    return newImage


async def get_thumb(videoid):
    if os.path.isfile(f"cache/{videoid}.png"):
        return f"cache/{videoid}.png"

    url = f"https://www.youtube.com/watch?v={videoid}"
    try:
        results = VideosSearch(url, limit=1)
        for result in (await results.next())["result"]:
            try:
                title = result["title"]
                title = re.sub(r"\W+", " ", title)
                title = title.title()
            except:
                title = "Unsupported Title"
            try:
                duration = result["duration"]
            except:
                duration = "Unknown"
            thumbnail = result["thumbnails"][0]["url"].split("?")[0]
            try:
                views = result["viewCount"]["short"]
            except:
                views = "Unknown Views"

        async with aiohttp.ClientSession() as session:
            async with session.get(thumbnail) as resp:
                if resp.status == 200:
                    f = await aiofiles.open(f"cache/thumb{videoid}.png", mode="wb")
                    await f.write(await resp.read())
                    await f.close()

        youtube = Image.open(f"cache/thumb{videoid}.png")

        GLOW_COLOR = "#ff0099"  # Neon Pink
        BORDER_COLOR = "#FF1493"  # Deep Pink
        image1 = changeImageSize(1280, 720, youtube)
        image1 = image1.filter(ImageFilter.GaussianBlur(20))
        image1 = ImageEnhance.Brightness(image1).enhance(0.4)

        thumb_width = 840
        thumb_height = 460

        youtube_thumb = youtube.resize((thumb_width, thumb_height))

        mask = Image.new("L", (thumb_width, thumb_height), 0)
        draw_mask = ImageDraw.Draw(mask)
        draw_mask.rounded_rectangle(
            [(0, 0), (thumb_width, thumb_height)], radius=20, fill=255
        )
        youtube_thumb.putalpha(mask)
        center_x = 640
        center_y_img = 300
        thumb_x = center_x - (thumb_width // 2)
        thumb_y = center_y_img - (thumb_height // 2)
        thumb_x2 = thumb_x + thumb_width
        thumb_y2 = thumb_y + thumb_height

        glow_layer = Image.new("RGBA", (1280, 720), (0, 0, 0, 0))
        draw_glow = ImageDraw.Draw(glow_layer)

        glow_expand = 20
        draw_glow.rounded_rectangle(
            [
                (thumb_x - glow_expand, thumb_y - glow_expand),
                (thumb_x2 + glow_expand, thumb_y2 + glow_expand),
            ],
            radius=30,
            fill=GLOW_COLOR,
        )
        glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(30))
        image1.paste(glow_layer, (0, 0), glow_layer)
        border_layer = Image.new("RGBA", (1280, 720), (0, 0, 0, 0))
        draw_border = ImageDraw.Draw(border_layer)

        border_expand = 5
        draw_border.rounded_rectangle(
            [
                (thumb_x - border_expand, thumb_y - border_expand),
                (thumb_x2 + border_expand, thumb_y2 + border_expand),
            ],
            radius=25,
            fill=BORDER_COLOR,
        )
        image1.paste(border_layer, (0, 0), border_layer)

        image1.paste(youtube_thumb, (thumb_x, thumb_y), youtube_thumb)

        draw = ImageDraw.Draw(image1)

        try:
            font_title = ImageFont.truetype("AloneMusic/assets/font.ttf", 45)
            font_details = ImageFont.truetype("AloneMusic/assets/font2.ttf", 30)
            font_watermark = ImageFont.truetype("AloneMusic/assets/font2.ttf", 25)
        except:
            font_title = ImageFont.truetype("arial.ttf", 45)
            font_details = ImageFont.truetype("arial.ttf", 30)
            font_watermark = ImageFont.truetype("arial.ttf", 25)

        def get_text_width(text, font):
            if hasattr(draw, "textlength"):
                return draw.textlength(text, font=font)
            else:
                return draw.textsize(text, font=font)[0]

        if len(title) > 45:
            title = title[:45] + "..."

        w_title = get_text_width(title, font_title)
        text_y_pos = thumb_y2 + 50

        draw.text(
            ((1280 - w_title) / 2, text_y_pos),
            text=title,
            fill="white",
            font=font_title,
            stroke_width=1,
            stroke_fill="black",
        )

        stats_text = f"YouTube : {views} | Time : {duration} | Player : @aashikmusicbot"
        w_stats = get_text_width(stats_text, font_details)
        draw.text(
            ((1280 - w_stats) / 2, text_y_pos + 70),
            text=stats_text,
            fill=BORDER_COLOR,
            font=font_details,
            stroke_width=1,
            stroke_fill="black",
        )

        text_classy = "AloneMusic"
        w_classy = get_text_width(text_classy, font_watermark)

        draw.text(
            (1280 - w_classy - 30, 30),
            text=text_classy,
            fill="yellow",
            font=font_watermark,
            stroke_width=1,
            stroke_fill="black",
        )

        draw.text(
            (30, 680),
            text="AloneMusic",
            fill="white",
            font=font_watermark,
            stroke_width=1,
            stroke_fill="black",
        )

        try:
            os.remove(f"cache/thumb{videoid}.png")
        except:
            pass

        file_name = f"cache/{videoid}.png"
        image1.save(file_name)
        return file_name

    except Exception as e:
        print(e)
        return YOUTUBE_IMG_URL


async def get_qthumb(vidid):
    try:
        url = f"https://www.youtube.com/watch?v={vidid}"
        results = VideosSearch(url, limit=1)
        for result in (await results.next())["result"]:
            thumbnail = result["thumbnails"][0]["url"].split("?")[0]
        return thumbnail
    except Exception as e:
        print(e)
        return YOUTUBE_IMG_URL
