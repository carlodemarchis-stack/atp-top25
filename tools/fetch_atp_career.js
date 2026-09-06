// Run in the browser on https://www.atptour.com (Cloudflare-cleared).
// Produces {id:{cw,cl,ct,cp}} — TRUE career totals for the ATP card app.
// NOTE: /activity/sgl/<id>/2026 is year-scoped; its *Total fields equal the season values.
// Career must come from the /all variant. Career prize = sgl.Prize + dbl.Prize (as ATP displays).
window.__ids = [/* paste the 100 ids from data/players.json */];
window.__career = {};
window.__grab = async function(from,to){
  const g=async u=>{ try{ const r=await fetch(u,{headers:{accept:'application/json'}}); return r.ok? await r.json():null; }catch(e){ return null; } };
  const ids=window.__ids.slice(from,to);
  for(let i=0;i<ids.length;i+=4){
    await Promise.all(ids.slice(i,i+4).map(async id=>{
      const [s,d]=await Promise.all([g(`/en/-/www/activity/sgl/${id}/all`), g(`/en/-/www/activity/dbl/${id}/all`)]);
      if(s) window.__career[id]={cw:s.Won, cl:s.Lost, ct:s.Titles, cp:(s.Prize||0)+((d&&d.Prize)||0)};
    }));
    await new Promise(r=>setTimeout(r,250));   // stay under the rate limit
  }
  return Object.keys(window.__career).length;
};
// await window.__grab(0,25); ... in chunks of 25, then JSON.stringify(window.__career)
