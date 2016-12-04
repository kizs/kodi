cd ..
zip -r plugin.video.huncoretv.zip plugin.video.huncoretv
mv plugin.video.huncoretv.zip releases
#md5sum -b plugin.video.huncoretv-1.5.zip > plugin.video.huncoretv-1.5.md5

zip -r plugin.video.bithumentv.zip plugin.video.bithumentv
mv plugin.video.bithumentv.zip releases
#md5sum -b plugin.video.bithumentv-1.4.zip > plugin.video.bithumentv-1.4.md5

zip -r service.kizstorrent.zip service.kizstorrent
mv service.kizstorrent.zip releases

zip -r releases/plugin.video.animeaddicts-1.1.zip plugin.video.animeaddicts
#md5sum -b plugin.video.animeaddicts-1.0.zip > plugin.video.animeaddicts-1.0.md5
cd releases