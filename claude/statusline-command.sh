#!/bin/sh
# Claude Code status line — jellybeans theme, two lines.
#   Line 1: model · effort · thinking · fast · context-bar(1-decimal %) · +/- · $cost · plan 5h/7d
#   Line 2: ~/dir on branch@commit "commit title…" ✓ · HH:MM:SS
# 5h plan resets show as countdown; 7d shows a date until <=12h left, then countdown.

input=$(cat)

# ---- jellybeans truecolor palette -----------------------------------------
e=$(printf '\033')
R="${e}[0m"; D="${e}[2m"; B="${e}[1m"; I="${e}[3m"
cream="${e}[38;2;232;232;211m"
orange="${e}[38;2;255;185;100m"
green="${e}[38;2;153;173;106m"
red="${e}[38;2;207;106;76m"
blue="${e}[38;2;129;151;191m"
cyan="${e}[38;2;143;191;220m"
purple="${e}[38;2;198;182;238m"
pink="${e}[38;2;240;160;192m"
gray="${e}[38;2;136;136;136m"
yellow="${e}[38;2;250;208;122m"
sep="${gray}·${R}"

# ---- pull fields -----------------------------------------------------------
cwd=$(echo "$input"      | jq -r '.workspace.current_dir // .cwd // ""')
model=$(echo "$input"    | jq -r '.model.display_name // ""')
effort=$(echo "$input"   | jq -r '.effort.level // empty')
thinking=$(echo "$input" | jq -r '.thinking.enabled // false')
fast=$(echo "$input"     | jq -r '.fast_mode // false')
style=$(echo "$input"    | jq -r '.output_style.name // "default"')
cost=$(echo "$input"     | jq -r '.cost.total_cost_usd // empty')
added=$(echo "$input"    | jq -r '.cost.total_lines_added // 0')
removed=$(echo "$input"  | jq -r '.cost.total_lines_removed // 0')
used_tok=$(echo "$input" | jq -r '.context_window.total_input_tokens // empty')
ctx_size=$(echo "$input" | jq -r '.context_window.context_window_size // empty')
used_pct=$(echo "$input" | jq -r '.context_window.used_percentage // empty')
rl5=$(echo "$input"      | jq -r '.rate_limits.five_hour.used_percentage // empty')
rl7=$(echo "$input"      | jq -r '.rate_limits.seven_day.used_percentage // empty')
rl5_at=$(echo "$input"   | jq -r '.rate_limits.five_hour.resets_at // empty')
rl7_at=$(echo "$input"   | jq -r '.rate_limits.seven_day.resets_at // empty')

hum() { awk -v t="$1" 'BEGIN{ if(t>=1000000) printf "%.1fM",t/1e6; else if(t>=1000) printf "%.0fk",t/1e3; else printf "%d",t }'; }
pctcolor() { [ "$1" -ge 80 ] && printf '%s' "$red" && return; [ "$1" -ge 50 ] && printf '%s' "$yellow" && return; printf '%s' "$green"; }
reset_t() { [ -n "$1" ] && date -r "$1" "+$2" 2>/dev/null; }
remain_t() {
    [ -n "$1" ] || return
    awk -v a="$1" -v n="$(date +%s)" 'BEGIN{
        d=a-n; if(d<0)d=0; h=int(d/3600); m=int((d%3600)/60);
        if(h>0) printf "%dh%dm",h,m; else printf "%dm",m }'
}

# ---- Line 1: Claude session settings --------------------------------------
line1="${B}${blue}✻ ${model}${R}"
[ -n "$effort" ] && line1="${line1} ${sep} ${pink}⚙ ${effort}${R}"
if [ "$thinking" = "true" ]; then
    line1="${line1} ${sep} ${green}think${R}"
else
    line1="${line1} ${sep} ${gray}think off${R}"
fi
[ "$fast" = "true" ]      && line1="${line1} ${sep} ${cyan}⚡fast${R}"
[ "$style" != "default" ] && line1="${line1} ${sep} ${purple}${style}${R}"

# context bar with 1-decimal percent — how close to auto-compact
pct=""
if [ -n "$used_tok" ] && [ -n "$ctx_size" ] && [ "$ctx_size" != "0" ]; then
    pct=$(awk -v t="$used_tok" -v s="$ctx_size" 'BEGIN{printf "%.1f", t/s*100}')
elif [ -n "$used_pct" ] && [ "$used_pct" != "null" ]; then
    pct=$(printf '%.1f' "$used_pct")
fi
if [ -n "$pct" ]; then
    pint=${pct%.*}
    filled=$(awk -v p="$pint" 'BEGIN{f=int(p/10+0.5); if(f>10)f=10; if(f<0)f=0; print f}')
    bar=""; i=0
    while [ "$i" -lt 10 ]; do
        if [ "$i" -lt "$filled" ]; then bar="${bar}█"; else bar="${bar}░"; fi
        i=$((i+1))
    done
    bc=$(pctcolor "$pint")
    ctxlabel=""
    [ -n "$used_tok" ] && [ -n "$ctx_size" ] && ctxlabel=" ${D}$(hum "$used_tok")/$(hum "$ctx_size")${R}"
    line1="${line1} ${sep} ${bc}${bar}${R} ${pct}%${ctxlabel}"
fi

# 항상 표시 (편집 전이면 +0/-0)
line1="${line1} ${sep} ${green}+${added}${R}${D}/${R}${red}-${removed}${R}"

# ---- cost + plan usage (appended to line 1) -------------------------------
[ -n "$cost" ] && [ "$cost" != "null" ] && \
    line1="${line1} ${sep} ${green}\$$(printf '%.2f' "$cost")${R}"

# plan은 항상 표시. 데이터가 아직 없으면(세션 시작 직후) … 플레이스홀더.
# 5h: always countdown. 7d: countdown only when <=12h left, else absolute date.
now=$(date +%s)
if [ -n "$rl5" ]; then
    rl5d=$(printf '%.1f' "$rl5"); rl5i=${rl5d%.*}   # 표시는 소수 1자리, 색상은 정수부로
    c=$(pctcolor "$rl5i"); t=$(remain_t "$rl5_at")
    p5="${gray}5h${R} ${c}${rl5d}%${R}${t:+ ${D}↻${t}${R}}"
else
    p5="${gray}5h${R} ${D}…${R}"
fi
if [ -n "$rl7" ]; then
    rl7d=$(printf '%.1f' "$rl7"); rl7i=${rl7d%.*}
    c=$(pctcolor "$rl7i")
    if [ -n "$rl7_at" ] && [ "$((rl7_at - now))" -le 43200 ]; then
        t=$(remain_t "$rl7_at")
    else
        t=$(reset_t "$rl7_at" "%m/%d %H:%M")
    fi
    p7="${gray}7d${R} ${c}${rl7d}%${R}${t:+ ${D}↻${t}${R}}"
else
    p7="${gray}7d${R} ${D}…${R}"
fi
line1="${line1} ${sep} ${gray}plan${R} ${p5} ${sep} ${p7}"

# ---- Line 2: place (dir + git + commit title + time) ----------------------
home="$HOME"; short_cwd="${cwd/#$home/~}"

git_seg=""
if [ -n "$cwd" ] && git -C "$cwd" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    branch=$(git -C "$cwd" rev-parse --abbrev-ref HEAD 2>/dev/null)
    commit=$(git -C "$cwd" rev-parse --short HEAD 2>/dev/null)
    subject=$(git -C "$cwd" log -1 --format=%s 2>/dev/null)
    maxlen=58
    if [ -n "$subject" ] && [ "${#subject}" -gt "$maxlen" ]; then
        subject="${subject:0:$((maxlen-1))}…"
    fi
    if [ -n "$(git -C "$cwd" status --porcelain 2>/dev/null)" ]; then
        mark=" ${red}✗${R}"
    else
        mark=" ${green}✓${R}"
    fi
    git_seg=" ${gray}on${R} ${purple}${branch}${R}"
    [ -n "$commit" ] && git_seg="${git_seg}${D}@${commit}${R}"
    [ -n "$subject" ] && git_seg="${git_seg} ${gray}${I}${subject}${R}"
    git_seg="${git_seg}${mark}"
fi

time=$(date +%H:%M:%S)
line2="${orange}${short_cwd}${R}${git_seg} ${sep} ${cyan}${time}${R}"

printf '%b\n%b\n' "$line1" "$line2"
