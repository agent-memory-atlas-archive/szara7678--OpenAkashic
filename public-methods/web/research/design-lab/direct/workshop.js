
'use strict';
const byId=id=>document.getElementById(id);
const form=byId('booking-form');
const fields={name:byId('name'),email:byId('email'),people:byId('people')};
const panels=['entry','review','complete'];
const money=n=>new Intl.NumberFormat('ko-KR').format(n)+'원';
let reservation=null;
function show(panel){panels.forEach(id=>byId(id).hidden=id!==panel);document.title=({entry:'느린손 — 예약 입력',review:'느린손 — 입력 내용 확인',complete:'모의 예약 완료 — 느린손'})[panel];byId(panel+'-heading').focus();}
function validPeople(){return /^[1-4]$/.test(fields.people.value.trim());}
function updateTotal(){byId('live-total').textContent=validPeople()?money(Number(fields.people.value.trim())*28000):'인원을 입력해 주세요';}
function clearErrors(){byId('error-summary').hidden=true;byId('error-list').replaceChildren();['name','email','time','people'].forEach(key=>{const el=byId(key+'-error');el.hidden=true;el.textContent='';});Object.values(fields).forEach(el=>el.removeAttribute('aria-invalid'));['time11','time15'].forEach(id=>byId(id).removeAttribute('aria-invalid'));}
function renderSummary(target){const dl=byId(target);dl.replaceChildren();const rows=[['체험','손제본 90분'],['이름',reservation.name],['이메일',reservation.email],['날짜','2026년 11월 14일 토요일'],['시간',reservation.time],['인원',reservation.people+'명'],['총액',money(reservation.people*28000)+' (재료 포함)'],['결제','당일 현장 결제']];rows.forEach(([label,value])=>{const row=document.createElement('div'),dt=document.createElement('dt'),dd=document.createElement('dd');dt.textContent=label;dd.textContent=value;row.append(dt,dd);dl.append(row);});}
form.addEventListener('submit',event=>{event.preventDefault();clearErrors();const errors=[];const name=fields.name.value.trim(),email=fields.email.value.trim(),people=fields.people.value.trim();const selected=form.querySelector('input[name="time"]:checked');if(!name)errors.push(['name','이름을 입력해 주세요.','name']);if(!email)errors.push(['email','이메일을 입력해 주세요.','email']);else if(!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)||fields.email.validity.typeMismatch)errors.push(['email','이메일을 hello@example.com 형태로 입력해 주세요.','email']);if(!selected)errors.push(['time','11:00 또는 15:00 중 시간을 선택해 주세요.','time11']);if(!people)errors.push(['people','인원을 입력해 주세요.','people']);else if(!validPeople())errors.push(['people','인원은 1~4 사이의 정수로 입력해 주세요.','people']);if(errors.length){errors.forEach(([key,message,focusId])=>{const error=byId(key+'-error');error.textContent='오류: '+message;error.hidden=false;if(key==='time'){['time11','time15'].forEach(id=>byId(id).setAttribute('aria-invalid','true'));}else fields[key].setAttribute('aria-invalid','true');const li=document.createElement('li'),link=document.createElement('a');link.href='#'+focusId;link.textContent=message;link.addEventListener('click',event=>{event.preventDefault();byId(focusId).focus();});li.append(link);byId('error-list').append(li);});byId('error-summary').hidden=false;document.title='입력 오류 '+errors.length+'개 — 느린손';byId('error-summary').focus();return;}reservation={name,email,time:selected.value,people:Number(people)};renderSummary('review-summary');show('review');});
fields.people.addEventListener('input',updateTotal);
byId('edit').addEventListener('click',()=>{show('entry');});
byId('confirm').addEventListener('click',()=>{if(!reservation)return;renderSummary('complete-summary');show('complete');});
function reset(){reservation=null;form.reset();Object.values(fields).forEach(el=>el.value='');form.querySelectorAll('input[type="radio"]').forEach(el=>el.checked=false);clearErrors();updateTotal();panels.forEach(id=>byId(id).hidden=id!=='entry');byId('review-summary').replaceChildren();byId('complete-summary').replaceChildren();document.title='느린손 — 주말 손제본 체험';}
byId('restart').addEventListener('click',()=>{reset();byId('entry-heading').focus();});
window.addEventListener('pageshow',reset);
reset();
