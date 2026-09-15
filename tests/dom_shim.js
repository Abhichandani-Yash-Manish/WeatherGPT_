'use strict';
/* Minimal DOM shim for component-level checks. This is not a browser: it exists
   so the renderers and the client wiring can be asserted without one. It models
   only what the workspace page actually uses, and it stays honest about being a
   shim by never claiming to test layout, styling or real browser behaviour. */

function parseSimple(selector) {
  const match = /^([a-zA-Z][\w-]*)?(?:#([\w-]+))?(?:\.([\w-]+))?(?:\[([\w-]+)="([^"]*)"\])?$/.exec(String(selector).trim());
  if (!match) return null;
  return { tag: match[1] || null, id: match[2] || null, cls: match[3] || null, attr: match[4] || null, value: match[5] };
}
function matchesSelector(node, selector) {
  return String(selector).split(',').some(part => {
    const spec = parseSimple(part);
    if (!spec) return false;
    if (spec.tag && node.tag !== spec.tag) return false;
    if (spec.id && node.id !== spec.id) return false;
    if (spec.cls && !node.classList.contains(spec.cls)) return false;
    if (spec.attr && node.attrs[spec.attr] !== spec.value) return false;
    return true;
  });
}

class ClassList {
  constructor(node) { this.node = node; }
  get set() { return this.node._classes; }
  add(...names) { names.forEach(name => this.node._classes.add(name)); }
  remove(...names) { names.forEach(name => this.node._classes.delete(name)); }
  contains(name) { return this.node._classes.has(name); }
  toggle(name, force) {
    const on = force === undefined ? !this.node._classes.has(name) : !!force;
    if (on) this.node._classes.add(name); else this.node._classes.delete(name);
    return on;
  }
  toString() { return Array.from(this.node._classes).join(' '); }
}

class Node {
  constructor(tag) {
    this.tag = tag;
    // Faithful enough that element cells are recognised by nodeType, as a browser does.
    this.nodeType = tag === '#text' ? 3 : 1;
    this.id = '';
    this._classes = new Set();
    this._text = '';
    this.children = [];
    this.attrs = {};
    this.events = {};
    this.dataset = {};
    this.hidden = false;
    this.open = false;
    this.value = '';
    this.focused = false;
    this.parent = null;
    this.scrollTop = 0;
    this.scrollHeight = 0;
    this.clientHeight = 0;
    this.href = '';
    this.download = '';
    this.rel = '';
    this.target = '';
    this.type = '';
    this.className = '';
  }
  get classList() { return new ClassList(this); }
  get className() { return Array.from(this._classes).join(' '); }
  set className(value) {
    this._classes = new Set(String(value || '').split(/\s+/).filter(Boolean));
  }
  get textContent() {
    if (this._text) return this._text + this.children.map(child => child.textContent || '').join('');
    return this.children.map(child => child.textContent || '').join('');
  }
  set textContent(value) {
    this._text = value === undefined || value === null ? '' : String(value);
    this.children = [];
  }
  get childNodes() { return this.children; }
  get firstChild() { return this.children[0] || null; }
  append(...nodes) {
    nodes.forEach(node => {
      if (node === undefined || node === null) return;
      if (typeof node === 'string') { this._text += node; return; }
      node.parent = this;
      this.children.push(node);
    });
  }
  appendChild(node) { this.append(node); return node; }
  insertBefore(node, reference) {
    const index = reference ? this.children.indexOf(reference) : -1;
    if (index < 0) this.children.push(node); else this.children.splice(index, 0, node);
    node.parent = this;
    return node;
  }
  replaceChildren(...nodes) { this.children = []; this._text = ''; this.append(...nodes); }
  remove() {
    if (this.parent) this.parent.children = this.parent.children.filter(child => child !== this);
    this.parent = null;
  }
  setAttribute(key, value) {
    this.attrs[key] = String(value);
    if (key === 'class') this.className = value;
    if (key === 'id') this.id = String(value);
    // A browser reflects common attributes onto the element as properties, and the
    // workspace reads meta.content and link.href directly, so the shim does too.
    if (['content', 'href', 'src', 'rel', 'target', 'download', 'title', 'type', 'value'].indexOf(key) >= 0) {
      this[key] = String(value);
    }
  }
  getAttribute(key) { return key in this.attrs ? this.attrs[key] : null; }
  hasAttribute(key) { return key in this.attrs; }
  addEventListener(event, handler) {
    (this.events[event] = this.events[event] || []).push(handler);
  }
  dispatch(event, detail) {
    const handlers = this.events[event] || [];
    handlers.forEach(handler => handler(Object.assign({ currentTarget: this, preventDefault() {}, stopPropagation() {} }, detail || {})));
    return handlers.length;
  }
  focus() { this.focused = true; }
  click() { this.dispatch('click'); }
  select() {}
  querySelectorAll(selector) {
    const found = [];
    const walk = node => node.children.forEach(child => {
      if (matchesSelector(child, selector)) found.push(child);
      walk(child);
    });
    walk(this);
    return found;
  }
  querySelector(selector) { return this.querySelectorAll(selector)[0] || null; }
  closest(selector) {
    let node = this;
    while (node) { if (matchesSelector(node, selector)) return node; node = node.parent; }
    return null;
  }
  all(tag) {
    const found = this.tag === tag ? [this] : [];
    return found.concat(this.children.flatMap(child => (child.all ? child.all(tag) : [])));
  }
  getBoundingClientRect() { return { top:0, left:0, right:0, bottom:0, width:0, height:0 }; }
}

function createDocument() {
  const registry = {};
  const document = {
    readyState: 'complete',
    body: new Node('body'),
    documentElement: new Node('html'),
    createElement: tag => new Node(tag),
    createTextNode: text => { const node = new Node('#text'); node.textContent = String(text); return node; },
    createElementNS: (namespace, tag) => new Node(tag),
    getElementById: id => {
      if (!registry[id]) { const node = new Node('div'); node.id = id; registry[id] = node; }
      return registry[id];
    },
    querySelector: selector => {
      if (/meta\[name="workspace-token"\]/.test(selector)) {
        const meta = new Node('meta');
        meta.setAttribute('content', 'test-token');
        return meta;
      }
      return null;
    },
    querySelectorAll: () => [],
    addEventListener: () => {},
    removeEventListener: () => {},
    _registry: registry
  };
  return document;
}

module.exports = { Node, createDocument, matchesSelector };
