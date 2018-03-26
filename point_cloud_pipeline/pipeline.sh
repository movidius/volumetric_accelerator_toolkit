DROPPATH="/home/"$USER"/Documents/vola/drop/"

ls $DROPPATH | grep ".las\|.laz\|.vol" | xargs -P 6 -I % python pipefile.py $DROPPATH% &
inotifywait -m -e moved_to -e close_write $DROPPATH --format "%w%f" | xargs -P 6 -I % python pipefile.py %
