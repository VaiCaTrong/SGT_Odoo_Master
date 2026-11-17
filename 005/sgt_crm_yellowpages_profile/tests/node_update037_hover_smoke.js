/* Minimal event/DOM harness for testing CRM-005's delegated Kanban hover logic.
   Not a replacement for staging browser or Odoo tests. */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const source = fs.readFileSync(path.resolve(__dirname, '../static/src/js/sgt_marquee.js'), 'utf8');
const listeners = {};
const pending = [];
const frames = [];
const window = {
  matchMedia() { return {matches:false}; },
  getComputedStyle(node) { return {overflowX:node.overflowX || 'visible'}; },
  setTimeout(callback) { pending.push(callback); return pending.length; },
  clearTimeout() {},
  requestAnimationFrame(callback) { frames.push(callback); return frames.length; },
  cancelAnimationFrame() {},
};
const document = {
  activeElement: null,
  addEventListener(name, callback) { listeners[name] = callback; },
};
vm.runInNewContext(source, {document, window});

class Element {
  constructor(classes, parent=null) {
    this.nodeType=1;this.classNames = new Set(classes.split(' ').filter(Boolean));
    this.parentElement=parent;this.children=[];this.scrollWidth=20;this.clientWidth=20;this.scrollLeft=0;
    this.overflowX='visible';this.tagName='DIV';this.isContentEditable=false;
    if(parent)parent.children.push(this);
  }
  closest(selector) {
    const parts=selector.split('.').filter(Boolean);
    for(let n=this;n;n=n.parentElement){if(parts.every(x=>n.classNames.has(x)))return n;}
    return null;
  }
  contains(node){for(let p=node;p;p=p.parentElement){if(p===this)return true;}return false;}
  querySelector(selector){const parts=selector.split('.').filter(Boolean);const search=node=>{
    for(const child of node.children){if(parts.every(x=>child.classNames.has(x)))return child;const found=search(child);if(found)return found;}
    return null;
  };return search(this);}
  getAttribute(){return null;}
  get classList(){return {add:(v)=>this.classNames.add(v),remove:(v)=>this.classNames.delete(v)};}
}
function fire(type,target,relatedTarget=null){assert(listeners[type]);listeners[type]({target,relatedTarget,buttons:0});}
function tick(){while(pending.length)pending.shift()();}
function frameTick(t){if(frames.length)frames.shift()(t);}

const root = new Element('o_opportunity_kanban');
const card = new Element('o_kanban_record',root);
const logo = new Element('sgt_crm005_kanban_logo',card);
// Update_046: company name is deliberately NOT marked with sgt_marq.
const company = new Element('sgt_crm005_kanban_company_name',card);
company.scrollWidth=500;company.clientWidth=130;company.overflowX='hidden';
const footer = new Element('o_kanban_footer',card);
const external = new Element('outside');
fire('mouseover',logo);tick();
assert(!company.classNames.has('sgt-marq-run'),'Hover must not animate the company name');
assert.equal(company.scrollLeft,0,'Company name must not scroll on logo hover');
fire('mouseover',company);tick();
assert(!company.classNames.has('sgt-marq-run'),'Direct name hover must not animate');
fire('mouseover',footer);tick();
assert.equal(company.scrollLeft,0,'Hovering other card parts must not scroll the name');
const shortCard=new Element('o_kanban_record',root);
const shortName=new Element('sgt_crm005_kanban_company_name',shortCard);
shortName.scrollWidth=70;shortName.clientWidth=130;shortName.overflowX='hidden';
fire('mouseover',shortCard);tick();
assert(!shortName.classNames.has('sgt-marq-run'),'Short company must not animate');

const formRoot = new Element('sgt_marq',external);
const formValue = new Element('',formRoot);
formValue.scrollWidth=320;formValue.clientWidth=100;formValue.overflowX='hidden';
fire('mouseover',external);tick();
assert(!formValue.classNames.has('sgt-marq-run'),'Non-kanban parent hover should not start legacy form marquee');
fire('mouseover',formValue);tick();
assert(formValue.classNames.has('sgt-marq-run'),'Legacy form-field direct hover must still work');
fire('mouseout',formValue,external);
assert(!formValue.classNames.has('sgt-marq-run'),'Legacy form-field leave must still stop');
console.log('Update_046 company still / legacy form marquee smoke test PASS');
