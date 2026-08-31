const fs = require('fs');
const path = require('path');
const os = require('os');
const readline = require('readline');

/**
 * Fast Streaming Node.js Parser for Antigravity Session Transcripts
 */
async function parseAntigravityProfile(customUser = null) {
  const homeDir = os.homedir();
  const brainDir = path.join(homeDir, '.gemini', 'antigravity', 'brain');

  let sessionDirs = [];
  try {
    const entries = await fs.promises.readdir(brainDir, { withFileTypes: true });
    sessionDirs = entries.filter(e => e.isDirectory()).map(e => e.name);
  } catch (err) {
    sessionDirs = [];
  }

  const dayTokens = {};
  let totalTokens = 0;
  let peakTokens = 0;
  let longestActiveSec = 0;
  let totalChats = 0;

  let commandsRun = 0;
  let filesModified = 0;

  const mcpUsage = {
    '@blender': 0,
    '@playwright': 0,
    '@after-effects': 0,
    '@stitch': 0,
    '@netlify': 0,
    '@sequential-thinking': 0,
    '@github': 0
  };

  for (const dirName of sessionDirs) {
    const transcriptPath = path.join(brainDir, dirName, '.system_generated', 'logs', 'transcript.jsonl');
    if (!fs.existsSync(transcriptPath)) continue;

    totalChats++;
    let sessionTokens = 0;
    let prevTs = null;
    let sessionActiveSec = 0;

    const fileStream = fs.createReadStream(transcriptPath, { encoding: 'utf8' });
    const rl = readline.createInterface({
      input: fileStream,
      crlfDelay: Infinity
    });

    for await (const line of rl) {
      if (!line || !line.trim()) continue;
      let step;
      try {
        step = JSON.parse(line);
      } catch (e) {
        continue;
      }

      let dStr = '2026-08-31';
      if (step.created_at) {
        try {
          const ts = new Date(step.created_at);
          if (!isNaN(ts.getTime())) {
            if (prevTs !== null) {
              const diffSec = (ts.getTime() - prevTs.getTime()) / 1000;
              if (diffSec > 0 && diffSec < 1800) {
                sessionActiveSec += diffSec;
              }
            }
            prevTs = ts;
            dStr = ts.toISOString().split('T')[0];
          }
        } catch (e) {}
      }

      const cLen = (step.content || '').length;
      const thLen = (step.thinking || '').length;
      const tcLen = JSON.stringify(step.tool_calls || []).length;
      const approxTokens = Math.max(80, Math.floor((cLen + thLen + tcLen) / 3.5));

      sessionTokens += approxTokens;
      totalTokens += approxTokens;
      dayTokens[dStr] = (dayTokens[dStr] || 0) + approxTokens;

      if (Array.isArray(step.tool_calls)) {
        for (const call of step.tool_calls) {
          const name = (call && call.name) ? call.name : String(call);
          if (name.includes('command')) commandsRun++;
          if (name.includes('file') || name.includes('write') || name.includes('replace')) filesModified++;

          const toolStr = JSON.stringify(call).toLowerCase();
          for (const mcpKey of Object.keys(mcpUsage)) {
            const cleanKey = mcpKey.replace('@', '');
            if (toolStr.includes(cleanKey)) {
              mcpUsage[mcpKey]++;
            }
          }
        }
      }
    }

    if (sessionTokens > peakTokens) peakTokens = sessionTokens;
    if (sessionActiveSec > longestActiveSec) longestActiveSec = sessionActiveSec;
  }

  // 52-week Heatmap Grid aligned to today
  const today = new Date();
  const startDate = new Date(today);
  startDate.setDate(today.getDate() - 52 * 7);
  while (startDate.getDay() !== 0) { // Sunday
    startDate.setDate(startDate.getDate() - 1);
  }

  const weeks = [];
  let curr = new Date(startDate);
  let cumulative = 0;

  while (curr <= today || weeks.length < 52) {
    const week = [];
    for (let d = 0; d < 7; d++) {
      const dStr = curr.toISOString().split('T')[0];
      const tCount = dayTokens[dStr] || 0;
      if (curr <= today) cumulative += tCount;

      let lvl = 0;
      if (tCount === 0) lvl = 0;
      else if (tCount < 10000) lvl = 1;
      else if (tCount < 40000) lvl = 2;
      else if (tCount < 80000) lvl = 3;
      else lvl = 4;

      week.push({
        date: dStr,
        tokens: tCount,
        level: lvl,
        cumulative: cumulative
      });
      curr.setDate(curr.getDate() + 1);
    }
    weeks.push(week);
    if (weeks.length === 52) break;
  }

  // Streak calculations
  const sortedDays = Object.keys(dayTokens).filter(d => dayTokens[d] > 0).sort();
  let currentStreak = 0;
  let longestStreak = 0;
  let currRun = 0;

  if (sortedDays.length > 0) {
    let prevDate = null;
    for (const dS of sortedDays) {
      const dObj = new Date(dS + 'T00:00:00');
      if (!prevDate) {
        currRun = 1;
      } else {
        const diffDays = Math.round((dObj - prevDate) / (1000 * 60 * 60 * 24));
        if (diffDays === 1) {
          currRun++;
        } else if (diffDays > 1) {
          currRun = 1;
        }
      }
      if (currRun > longestStreak) longestStreak = currRun;
      prevDate = dObj;
    }

    let checkDate = new Date(today);
    let checkStr = checkDate.toISOString().split('T')[0];
    while (dayTokens[checkStr] > 0) {
      currentStreak++;
      checkDate.setDate(checkDate.getDate() - 1);
      checkStr = checkDate.toISOString().split('T')[0];
    }
    if (currentStreak === 0) {
      const yesterday = new Date(today);
      yesterday.setDate(today.getDate() - 1);
      let yStr = yesterday.toISOString().split('T')[0];
      while (dayTokens[yStr] > 0) {
        currentStreak++;
        yesterday.setDate(yesterday.getDate() - 1);
        yStr = yesterday.toISOString().split('T')[0];
      }
    }
  }

  function fmtNum(n) {
    if (n >= 1000000) return (n / 1000000).toFixed(1).replace(/\.0$/, '') + 'M';
    if (n >= 1000) return (n / 1000).toFixed(1).replace(/\.0$/, '') + 'K';
    return String(n);
  }

  const hours = Math.floor(longestActiveSec / 3600);
  const minutes = Math.floor((longestActiveSec % 3600) / 60);
  const longestChatFmt = hours > 0 ? `${hours}h ${String(minutes).padStart(2, '0')}m` : `${minutes}m`;

  const pluginIcons = {
    '@blender': '🎨',
    '@playwright': '🌐',
    '@after-effects': '✨',
    '@stitch': '🧵',
    '@netlify': '⚡',
    '@sequential-thinking': '🧠',
    '@github': '🐙'
  };

  const pluginList = Object.keys(mcpUsage)
    .filter(k => mcpUsage[k] > 0)
    .map(k => ({ name: k, runs: mcpUsage[k], icon: pluginIcons[k] || '🔌' }))
    .sort((a, b) => b.runs - a.runs);

  const defaultUser = {
    name: 'gelios_g',
    handle: '@gelios_g',
    badge: 'Free',
    initials: 'GER',
    avatarColor: '#e67e22',
    avatarImg: null
  };

  const user = Object.assign({}, defaultUser, customUser || {});

  return {
    user: user,
    metrics: {
      lifetimeTokens: totalTokens,
      lifetimeTokensFormatted: fmtNum(totalTokens),
      peakTokens: peakTokens,
      peakTokensFormatted: fmtNum(peakTokens),
      longestChatSeconds: longestActiveSec,
      longestChatFormatted: longestChatFmt,
      currentStreak: totalChats > 0 ? Math.max(1, currentStreak) : 0,
      longestStreak: totalChats > 0 ? Math.max(1, longestStreak) : 0
    },
    insights: {
      mcpConnected: `${Math.max(1, pluginList.length + 1)} servers`,
      skillsInstalled: '52 skills',
      commandsRun: `${commandsRun} commands`,
      filesModified: `${filesModified} files`,
      totalChats: `${totalChats} chats`
    },
    plugins: pluginList.length > 0 ? pluginList : [{ name: '@antigravity', runs: 1, icon: '▲' }],
    heatmap: {
      weeks: weeks,
      shareWeeks: weeks.slice(-26)
    }
  };
}

if (require.main === module) {
  const startTime = Date.now();
  parseAntigravityProfile().then(data => {
    console.log(`Parsed ${data.insights.totalChats} in ${Date.now() - startTime}ms`);
    console.log('Lifetime tokens:', data.metrics.lifetimeTokensFormatted);
    console.log('Peak tokens:', data.metrics.peakTokensFormatted);
    console.log('Longest chat:', data.metrics.longestChatFormatted);
    console.log('Streaks:', `${data.metrics.currentStreak} current / ${data.metrics.longestStreak} longest`);
    console.log('Insights:', JSON.stringify(data.insights));
    console.log('Top plugins:', data.plugins.map(p => `${p.name} (${p.runs})`).join(', '));
  });
}

module.exports = { parseAntigravityProfile };
