DROPPATH="/home/"$USER"/Documents/vola/drop/"
PROCNUM=6

ls $DROPPATH | grep ".las\|.laz\|.vol" | xargs -P $PROCNUM -I % python pipefile.py $DROPPATH% &
inotifywait -m -e moved_to -e close_write $DROPPATH --format "%w%f" | xargs -P $PROCNUM -I % python pipefile.py %
