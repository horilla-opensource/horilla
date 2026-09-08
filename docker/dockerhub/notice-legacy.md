## ⚠️ This repository has moved

The official image is now **[`horilla/horilla-hr`](https://hub.docker.com/r/horilla/horilla-hr)**.

This mirror still receives every stable release, so existing `docker pull horilla/horilla` deployments keep working — nothing breaks today. But new tags, documentation and support all target `horilla/horilla-hr` first.

**To switch,** change the image name in your compose file or deployment:

```diff
- image: horilla/horilla:latest
+ image: horilla/horilla-hr:latest
```

Both names are built from the same commit and are byte-identical. The examples below use the new name.

> **Following an older guide?** The instruction to run `horilla/horilla:1.4` with `manage.py runserver` is obsolete — it pins a January 2026 image and uses Django's development server, which is not suitable for production. Use the Docker Compose setup below.
