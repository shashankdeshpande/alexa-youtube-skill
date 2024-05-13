# Alexa YouTube Skill
Alexa doesn't come with built-in support for YouTube, but with this skill, you can seamlessly play your favorite songs from YouTube on your Amazon Echo device.

This skill is readily available on the Alexa Skill Store. Just enable it and start using it hassle-free.

[![Streamlit App](https://img.shields.io/badge/Open%20Alexa%20skill%20store-gray?logo=amazon)](https://www.amazon.in/dp/B0D1N3FTBK/)

## Getting Started
To launch the skill, simply use following phrases:
- Alexa, open music store
- Alexa, ask music store to play \<Artist Name\> songs

## Integrations
Here's how the functionality operates behind the scenes:
- Song Search: Utilizing [DuckDuckGo Search](https://pypi.org/project/duckduckgo-search/) to find the songs you request.
- Music Stream Link: The link to stream the music is fetched using [yt-dlp](https://pypi.org/project/yt-dlp/), an open-source library for YouTube content.
- Next Song Prediction: With the help of the [Rapid API](https://rapidapi.com/ytdlfree/api/youtube-v31/), the skill effortlessly queues up and predicts the next song for uninterrupted playback.

## Limitations
While striving for seamless performance, there are occasional limitations to keep in mind:

Currently, the skill relies on audio stream link retrieved from [yt-dlp](https://pypi.org/project/yt-dlp/), which may occasionally result in invalid link, leading to the inability to play songs sometimes.
