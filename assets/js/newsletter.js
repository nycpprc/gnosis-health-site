/* Inline Mailchimp signup via JSONP (/subscribe/post + &c=callback; /subscribe/post-json currently 404s). Without JS, forms fall back to a normal POST. */
(function(){
  function clean(s){var d=document.createElement('div');d.innerHTML=String(s||'');return (d.textContent||'').replace(/^\s*\d+\s*-\s*/,'').trim();}
  function nice(m){
    if(/already subscribed/i.test(m))return "You're already subscribed. Thanks!";
    if(/too many/i.test(m))return 'Too many attempts with this address. Please try again later.';
    return m||'Something went wrong. Please try again.';
  }
  document.querySelectorAll('form[action*="list-manage.com/subscribe/post"]').forEach(function(f){
    f.removeAttribute('target');
    var st=document.createElement('p');st.className='mc-status';st.setAttribute('role','status');st.setAttribute('aria-live','polite');
    f.parentNode.insertBefore(st,f.nextSibling);
    f.addEventListener('submit',function(e){
      e.preventDefault();
      var btn=f.querySelector('[type=submit]');if(btn&&btn.disabled)return;
      var cb='mcCb'+Date.now()+Math.floor(Math.random()*1e4);
      var url=f.action+'&c='+cb+'&'+new URLSearchParams(new FormData(f)).toString();
      var s=document.createElement('script'),done=false;
      function end(ok,msg){if(done)return;done=true;try{delete window[cb];}catch(x){window[cb]=undefined;}s.remove();clearTimeout(t);
        if(btn)btn.disabled=false;st.textContent=msg;st.className='mc-status '+(ok?'mc-ok':'mc-err');if(ok)f.reset();}
      window[cb]=function(r){r=r||{};if(r.result==='success'&&typeof window.gtag==='function'){try{var em=f.querySelector('input[type=email]');window.gtag('event','sign_up',{method:'newsletter',form_location:(f.getAttribute('data-form-location')||(em&&em.id||'').replace(/-email$/,'')||location.pathname)});}catch(x){}}end(r.result==='success',r.result==='success'?"Thanks, you're subscribed.":nice(clean(r.msg)));};
      var t=setTimeout(function(){end(false,'Could not reach the signup service. Please try again.');},12000);
      s.onerror=function(){end(false,'Could not reach the signup service. Please try again.');};
      if(btn)btn.disabled=true;st.className='mc-status';st.textContent='Subscribing…';
      s.src=url;document.body.appendChild(s);
    });
  });
})();
