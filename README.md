# podcast.py

## Install

```text
cd ~/ && curl -O https://raw.githubusercontent.com/dough10/podcast.py/refs/heads/main/install.sh && bash install.sh && rm install.sh
```

<https://podcastindex.org/> to find xml addresses

### subscribe and prompt

```bash
podcast.py https://example.com/feed.xml 1
```

### subscribe without downloading

```bash
podcast.py https://example.com/feed.xml 1 0
```

### subscribe with download

```bash
podcast.py https://example.com/feed.xml 1 1
```

### unsubscribe and prompt

```bash
podcast.py https://example.com/feed.xml 2
```

### download all episodes in xml without subscribing

```bash
podcast.py https://example.com/feed.xml 3
```

### download newest episode without subscribing

```bash
podcast.py https://example.com/feed.xml 4
```

Automate subscriptions using a shell scipt

**subscribe.sh** example:

```bash
#!/bin/bash

urls=("https://feeds.megaphone.fm/VMP7924981569" "https://feed.podbean.com/tonyia/feed.xml" "https://feeds.simplecast.com/jn7O6Fnt")

for url in "${urls[@]}"; do
   podcast.py "$url" 1 1
done

```
