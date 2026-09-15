#!/bin/sh
# Live composer measurement at three viewports through the running Chrome session.
# Each state is pinned explicitly: top of the document, then the end of the document.
set -e
export HOME=/tmp/ab-home
BIN=agent-browser
SESSION=wg-frontend
OUT=/Users/yashabhichandani/Desktop/WeatherGPT/research/reviews/frontend-v2-20260915/after
JS='JSON.stringify({viewport:[innerWidth,innerHeight],top:Math.round(document.querySelector(".composer").getBoundingClientRect().top),bottom:Math.round(document.querySelector(".composer").getBoundingClientRect().bottom),height:Math.round(document.querySelector(".composer").getBoundingClientRect().height),position:getComputedStyle(document.querySelector(".composer")).position,scroll_y:Math.round(window.scrollY),scroll_height:document.documentElement.scrollHeight,theme:document.documentElement.getAttribute("data-theme")})'
$BIN --session $SESSION reload >/dev/null
sleep 1
$BIN --session $SESSION eval 'JSON.stringify({title:document.title,url:location.href,surfaces:document.querySelectorAll("[data-surface]").length,composer:!!document.querySelector(".composer")})'
for vp in "1440 1200" "768 1024" "390 844"; do
  set -- $vp
  $BIN --session $SESSION set viewport "$1" "$2" >/dev/null
  $BIN --session $SESSION eval 'window.scrollTo(0,0); "top"' >/dev/null
  sleep 1
  printf 'viewport %sx%s top      -> ' "$1" "$2"
  $BIN --session $SESSION eval "$JS"
  $BIN --session $SESSION screenshot "$OUT/composer-frame-$1x$2-top.png" >/dev/null
  $BIN --session $SESSION eval 'window.scrollTo(0, document.documentElement.scrollHeight); "end"' >/dev/null
  sleep 1
  printf 'viewport %sx%s end      -> ' "$1" "$2"
  $BIN --session $SESSION eval "$JS"
done
