#!/bin/bash

function update_version(){
    git reset --hard origin/master && git checkout master && git pull
    newHash=$(dirhash . -a md5 -i "/plugins/ .*/ _*/" -m "*.py *.html *.js *.go")
    echo "${1}-${newHash}" > VERSION.txt
}

read -p "[+] Enter a new version: " newVersion

for d in plugins/* ; do
    read -p "[+] Release $d (y/n)?" CONT
    if [ "$CONT" = "n" ]; then
        echo "[!] Skipping ${d}..."
        continue
    fi

    cd $d
    update_version $newVersion
    cd - > /dev/null
done

for d in plugins/* ; do
    git add $d
done
update_version $newVersion
