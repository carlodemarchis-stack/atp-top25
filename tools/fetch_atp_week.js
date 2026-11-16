// Weekly ATP capture — run in the browser on https://www.atptour.com (Cloudflare-cleared),
// e.g. via javascript_tool. Fills window.__act2 (activity, all ids) and window.__ent / window.__img
// (entrants). Set the two lists first, start it, then poll window.__done (takes ~60 s for 100 ids).
//
//   window.__ids  = the new top-100 ids, in ranking order
//   window.__news = ids not in data/players.json yet (entrants)
//
// Export each to a tool-result file (output is large, the padding forces the file):
//   '|||S|||'+JSON.stringify(window.__act2)+'|||E|||'+'X'.repeat(200000)
//   '|||S|||'+JSON.stringify({ent:window.__ent, img:window.__img})+'|||E|||'+'X'.repeat(200000)
// then re-emit as [{"text": json}] files (activity_clean.json / entrants_clean.json) and write each
// entrant's img (base64 PNG) to img/full/<id>.png — check the alpha channel before touching it.
// Then: python3 atp_update.py <YYYY-MM-DD> <entrants_clean.json> <activity_clean.json>
window.__act2 = {}; window.__ent = {}; window.__img = {}; window.__done = false;
window.__score = function(m){ const out=[]; for(let i=1;i<=5;i++){ const p=m['Set'+i+'Player'], o=m['Set'+i+'Opponent'], t=m['Set'+i+'Tie'];
  if(p==null && o==null) continue; let s=p+'-'+o; if(t!=null) s+='('+t+')'; out.push(s); } return out.join(' '); };
(async () => {
  const g = async u => { const c=new AbortController(); const tid=setTimeout(()=>c.abort(),20000);
    try{ const r=await fetch(u,{headers:{accept:'application/json'},signal:c.signal}); clearTimeout(tid);
      if(!r.ok) return {__status:r.status}; const j=await r.json(); return j===null?{__status:'null'}:j; }
    catch(e){ return {__status:'timeout'}; } };
  const b64 = async u => { try{ const r=await fetch(u); if(!r.ok) return 'ERR '+r.status; const b=await r.blob();
    return await new Promise(res=>{ const fr=new FileReader(); fr.onload=()=>res(fr.result); fr.readAsDataURL(b); }); }
    catch(e){ return 'ERR '+e.name; } };
  for (const id of (window.__news || [])) {
    const [hero, sgl, dbl] = await Promise.all([g(`/en/-/www/players/hero/${id}`), g(`/en/-/www/activity/sgl/${id}/?v=1`), g(`/en/-/www/activity/dbl/${id}/?v=1`)]);
    window.__ent[id] = {hero, act:sgl, all:sgl, allDbl:dbl};
    window.__img[id] = await b64(`/-/media/alias/player-gladiator-headshot/${id}`);
  }
  const ids = window.__ids;
  for (let i = 0; i < ids.length; i += 4) {
    await Promise.all(ids.slice(i, i + 4).map(async id => {
      const [y, d] = await Promise.all([g(`/en/-/www/activity/sgl/${id}/?v=1`), g(`/en/-/www/activity/dbl/${id}/?v=1`)]);
      if (!y || y.__status) { window.__act2[id] = {err:(y && y.__status) || 1}; return; }
      const yr = (y.Activity || []).find(x => String(x.EventYear) === '2026') || {};
      const T = (yr.Tournaments || []).map(t => ({ name:t.EventDisplayName||t.EventName, loc:t.Location, date:t.EventDate, type:t.EventType,
        surf:t.Surface, draw:t.SglDrawSize, seed:t.PlayerRank, pts:t.Points||0, res:(t.HiRound||{}).ShortName||'-', resL:(t.HiRound||{}).LongName||'-',
        won:t.Won||0, lost:t.Lost||0, title:!!t.CountableTitle, url:t.TournamentUrl, prize:t.Prize||0, cur:t.CurrSymbol||'$',
        M:(t.Matches||[]).map(m => { const rn=m.Round||{}, bye=!!m.IsBye; return { r:rn.ShortName, rL:rn.LongName, wl:m.WinLoss, bye,
          opp: bye ? '' : (((m.OpponentFirstInitial||'').trim()+'. '+(m.OpponentLastName||'').trim()).trim()),
          oc:m.OpponentNatlId, or:m.OpponentRank||null, sc: bye ? '' : window.__score(m), st:m.MatchStatsUrl }; }) }));
      const dOk = d && !d.__status;
      window.__act2[id] = {T, yw:yr.Won, yl:yr.Lost, yt:yr.Titles, yp:yr.PrizeMoney||0,
        cw:y.Won, cl:y.Lost, ct:y.Titles, cp:(y.Prize||0) + ((dOk && d.Prize) || 0)};
    }));
    await new Promise(r => setTimeout(r, 250));        // stay under the rate limit
  }
  window.__done = true;
})();
