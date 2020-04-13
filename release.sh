#!/bin/bash

function tag_version(){
    git add VERSION.txt
    git commit -m "Upgrading VERSION to ${1}. Release notes to follow." && git push origin master
    git tag $1 && git push origin $1
}

function update_version(){
    git pull && git checkout master && git reset --hard origin/master
    newHash=$(find . -type f \( -name "*.py" -o -name "*.html" \) -not -path "./plugins/*" -not -path "./.tox/*" -exec md5 {} \; | md5)
    echo "${1}-${newHash}" > VERSION.txt
    tag_version $1
}

read -p "[+] Enter a new version: " newVersion

for d in plugins/* ; do
    read -p "[+] Release $d (y/n)?" CONT
    if [ "$CONT" = "n" ]; then
        echo "[!] Not releasing ${d}"
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