#!/bin/sh
# Capability checks recorded for the batch: palette search, raw-packet drawer, map day switch.
set -e
export HOME=/tmp/ab-home
BIN=agent-browser
SESSION=wg-frontend
$BIN --session $SESSION eval 'location.hash = "#/assistant"; 1' >/dev/null
sleep 1
printf 'palette search -> '
$BIN --session $SESSION eval '(function(){document.getElementById("palette-open").click(); var input=document.getElementById("palette-input"); input.value="surat"; input.dispatchEvent(new Event("input",{bubbles:true})); return "typed";})()' >/dev/null
sleep 1
$BIN --session $SESSION eval '(function(){var body=document.getElementById("palette-body"); var items=Array.prototype.map.call(body.querySelectorAll(".palette-item"), function(n){return n.textContent;}); return JSON.stringify({items:items.length, groups:Array.prototype.map.call(body.querySelectorAll(".palette-group"), function(n){return n.textContent;}), sample:items.slice(0,3)});})()'
printf 'palette close  -> '
$BIN --session $SESSION eval '(function(){document.dispatchEvent(new KeyboardEvent("keydown",{key:"Escape",bubbles:true})); return JSON.stringify({hidden:document.getElementById("palette").hidden});})()'
printf 'raw inspector  -> '
$BIN --session $SESSION eval '(function(){var b=Array.prototype.filter.call(document.querySelectorAll("button"), function(n){return n.textContent==="Inspect the raw packet";})[0]; if(!b) return "no button"; b.click(); var d=document.getElementById("evidence-drawer"); var pre=d.querySelector("pre"); return JSON.stringify({drawer_open:!d.hidden, pre_chars:pre?pre.textContent.length:0, exact:!!pre && pre.textContent.indexOf("conversation_id")>=0, note:(d.querySelector(".field-note")||{}).textContent?true:false});})()'
$BIN --session $SESSION eval '(function(){document.getElementById("drawer-close").click(); return 1;})()' >/dev/null
printf 'map day 3      -> '
$BIN --session $SESSION eval '(function(){location.hash="#/map"; return 1;})()' >/dev/null
sleep 2
$BIN --session $SESSION eval '(function(){var s=document.querySelector(".map-toolbar select"); s.value="3"; s.dispatchEvent(new Event("change",{bubbles:true})); return 1;})()' >/dev/null
sleep 1
$BIN --session $SESSION eval '(function(){var status=document.querySelector(".map-status"); return JSON.stringify({status:(status?status.textContent:"").slice(0,120), yellow:document.querySelectorAll("path.w-yellow").length, unmapped:document.querySelectorAll("path.w-unmapped").length});})()'
