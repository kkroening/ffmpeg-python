#!/usr/bin/env bash
set -ex
CLONE_URL=$(git remote -v | grep origin | head -n1 | awk '{print $2}')
if [ ! -d gh-pages ]; then
    git clone -b gh-pages ${CLONE_URL} gh-pages
else
    (cd gh-pages && git pull origin gh-pages)
fi

cd gh-pages
rm -rf *
touch .nojekyll
cp -r ../html/* .
git add -A
git commit -m 'Update docs'
git push origin gh-pages
