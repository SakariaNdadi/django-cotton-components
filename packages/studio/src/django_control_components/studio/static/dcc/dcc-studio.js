/*
 * django-control-components — studio builder runtime.
 * Loaded only by {% dcc_studio_assets %}, never on a normal panel page.
 *
 * Alpine components:
 *   dccStudioDoc(bootId)   flat document (dashboard / resource) + undo/redo + save
 *   dccTree(bootId)        the nested block-tree editor (pages), on x-recurse
 *   dccSortable            pointer-events reorder of a flat <ul> of [data-node]
 * Alpine directive:
 *   x-recurse="<array>"    a self-referencing <template> — Alpine has none natively
 */
(function () {
  var MAX_DEPTH = 12; // mirrors deserialize._MAX_TREE_DEPTH

  function register() {
    if (!window.Alpine) return;

    // ---- x-recurse: a self-referencing template -------------------------
    // <ul x-recurse="node.slots.default" data-dcc-tpl="tpl-id"></ul>
    window.Alpine.directive(
      "recurse",
      (el, { expression }, { evaluate, effect, cleanup }) => {
        const tpl = document.getElementById(el.getAttribute("data-dcc-tpl"));
        if (!tpl) return;
        let mounted = [];
        effect(() => {
          const items = evaluate(expression) || [];
          mounted.forEach((n) => {
            window.Alpine.destroyTree(n);
            n.remove();
          });
          mounted = [];
          const depth = Number(el.dataset.dccDepth || 0);
          if (depth > MAX_DEPTH) return;
          for (const item of items) {
            const node = tpl.content.firstElementChild.cloneNode(true);
            node.dataset.dccDepth = depth + 1;
            window.Alpine.addScopeToNode(node, { node: item });
            el.appendChild(node);
            window.Alpine.initTree(node);
            mounted.push(node);
          }
        });
        cleanup(() => mounted.forEach((n) => window.Alpine.destroyTree(n)));
      },
    );

    // ---- the document store ------------------------------------------------
    window.Alpine.data("dccStudioDoc", (bootId) => ({
      doc: { items: [] },
      palette: {},
      revision: 0,
      selectedId: null,
      dirty: false,
      saving: false,
      error: "",
      history: [],
      future: [],
      _cfg: {},
      listKey: "items",

      init() {
        const boot = readJson(bootId);
        if (boot) {
          this.doc = boot.doc || { items: [] };
          this.palette = boot.palette || {};
          this.revision = boot.revision || 0;
          this._cfg = boot;
          if (boot.listKey) this.listKey = boot.listKey;
        }
        this.snapshot(true);
      },

      // -- the active list -------------------------------------------------
      useList(key) {
        this.listKey = key;
        this.selectedId = null;
      },
      list() {
        if (!Array.isArray(this.doc[this.listKey])) this.doc[this.listKey] = [];
        return this.doc[this.listKey];
      },
      setList(rows) {
        this.doc[this.listKey] = rows;
      },

      // -- selection --------------------------------------------------------
      select(id) {
        this.selectedId = id;
      },
      selectedNode() {
        return this.list().find((it) => it.id === this.selectedId) || null;
      },

      // -- mutation --------------------------------------------------------
      snapshot(initial) {
        const copy = JSON.parse(JSON.stringify(this.doc));
        if (!initial) {
          this.history.push(copy);
          if (this.history.length > 50) this.history.shift();
          this.future = [];
          this.dirty = true;
        } else {
          this.history = [copy];
        }
      },
      _newId() {
        return "n" + Date.now() + Math.floor(Math.random() * 1000);
      },
      addItem(kind) {
        const id = this._newId();
        this.list().push({
          id: id,
          label: titleCase(kind),
          icon: "",
          target: "",
          target_kind: kind,
          is_public: true,
        });
        this.snapshot();
        this.select(id);
      },
      isGroup(node) {
        return node && node.target_kind === "group";
      },
      // config-shaped nodes (widgets, columns, entries): {id, type, config}
      addNode(type) {
        const id = this._newId();
        this.list().push({ id: id, type: type, config: {} });
        this.snapshot();
        this.select(id);
      },
      nodeLabel(node) {
        if (!node) return "";
        if (node.config && node.config.name) return node.config.name;
        if (node.config && node.config.label) return node.config.label;
        return titleCase(node.type || "");
      },
      // palette entry for the selected node's type
      typeInfo(kind) {
        const node = this.selectedNode();
        if (!node) return null;
        const list = (this.palette && this.palette[kind]) || [];
        return list.find((t) => t.name === node.type) || null;
      },
      setConfig(key, value) {
        const node = this.selectedNode();
        if (!node) return;
        if (!node.config) node.config = {};
        if (value === "" || value === null) delete node.config[key];
        else node.config[key] = value;
        this.snapshot();
      },
      removeItem(id) {
        this.setList(this.list().filter((it) => it.id !== id));
        if (this.selectedId === id) this.selectedId = null;
        this.snapshot();
      },
      move(from, to) {
        const rows = this.list().slice();
        if (to < 0 || to >= rows.length || from === to) return;
        const [row] = rows.splice(from, 1);
        rows.splice(to, 0, row);
        this.setList(rows);
        this.snapshot();
      },
      touch() {
        // called from x-model @change on inspector fields
        this.snapshot();
      },
      undo() {
        if (this.history.length < 2) return;
        this.future.push(this.history.pop());
        this.doc = JSON.parse(JSON.stringify(this.history[this.history.length - 1]));
        this.dirty = true;
      },
      redo() {
        if (!this.future.length) return;
        const next = this.future.pop();
        this.history.push(next);
        this.doc = JSON.parse(JSON.stringify(next));
        this.dirty = true;
      },

      // -- persistence ---------------------------------------------------
      _post(url, extra) {
        const body = new URLSearchParams(
          Object.assign({ doc: JSON.stringify(this.doc), revision: this.revision }, extra || {})
        );
        return fetch(url, {
          method: "POST",
          headers: {
            "X-CSRFToken": this._cfg.csrfToken || "",
            "Content-Type": "application/x-www-form-urlencoded",
          },
          body: body,
        });
      },
      save() {
        if (this.saving) return;
        this.saving = true;
        this.error = "";
        this._post(this._cfg.saveUrl)
          .then((r) => r.json().then((data) => ({ ok: r.ok, status: r.status, data: data })))
          .then(({ ok, status, data }) => {
            this.saving = false;
            if (ok) {
              this.revision = data.revision != null ? data.revision : this.revision;
              this.dirty = false;
              document.body.dispatchEvent(new CustomEvent("dcc:toast", { detail: "Saved" }));
              this.refreshPreview();
            } else if (status === 409) {
              this.error = "Someone else saved a newer version — reload to continue.";
              if (data.doc) {
                this.doc = data.doc;
                this.revision = data.revision;
                this.snapshot(true);
                this.dirty = false;
              }
            } else if (data.errors) {
              this.error = data.errors.map((e) => (e.path ? e.path + ": " : "") + e.message).join("; ");
            } else {
              this.error = "Save failed.";
            }
          })
          .catch(() => {
            this.saving = false;
            this.error = "Save failed (network).";
          });
      },
      refreshPreview() {
        if (!this._cfg.previewUrl) return;
        this._post(this._cfg.previewUrl)
          .then((r) => r.text())
          .then((html) => {
            const target = document.getElementById("dcc-studio-preview");
            if (target) target.innerHTML = html;
          });
      },
      setConfigJson(key, raw) {
        try {
          this.setConfig(key, raw.trim() === "" ? "" : JSON.parse(raw));
          this.error = "";
        } catch (e) {
          this.error = key + ": invalid JSON";
        }
      },
    }));

    // ---- page builder: the nested block-tree editor --------------------
    // The tree renders through x-recurse (see the directive above); this store
    // owns the doc, selection, per-node collapse, structural edits and the
    // same dirty/undo/save/409/preview plumbing as dccStudioDoc.
    window.Alpine.data("dccTree", (bootId) => ({
      root: {},
      raw: "{}",
      showRaw: false,
      palette: {},
      revision: 0,
      selectedId: null,
      activeSlot: "",
      collapsed: {},
      dirty: false,
      saving: false,
      error: "",
      history: [],
      future: [],
      _cfg: {},

      init() {
        const boot = readJson(bootId) || {};
        this._cfg = boot;
        this.palette = boot.palette || {};
        this.revision = boot.revision || 0;
        const root = boot.doc && boot.doc.root;
        this.root = root && root.type ? root : { id: this._newId(), type: "AppShell", props: {}, slots: {} };
        this._syncRaw();
        this.snapshot(true);
      },

      // -- palette / slots -----------------------------------------------
      blockInfo(type) {
        return ((this.palette && this.palette.blocks) || []).find((b) => b.name === type) || null;
      },
      slotNames(type) {
        const info = this.blockInfo(type);
        return (info && info.slots) || [];
      },

      // -- tree walk ---------------------------------------------------
      _locate(id, node, parent, slot) {
        node = node || this.root;
        if (node.id === id) return { node: node, parent: parent || null, slot: slot || null };
        const slots = node.slots || {};
        for (const s of Object.keys(slots)) {
          for (const child of slots[s] || []) {
            const hit = this._locate(id, child, node, s);
            if (hit) return hit;
          }
        }
        return null;
      },
      selectedNode() {
        return this.selectedId ? (this._locate(this.selectedId) || {}).node || null : null;
      },
      select(id) {
        this.selectedId = id;
        const slots = this.slotNames((this.selectedNode() || {}).type);
        this.activeSlot = slots[0] || "";
      },
      isCollapsed(id) {
        return !!this.collapsed[id];
      },
      toggleCollapse(id) {
        this.collapsed[id] = !this.collapsed[id];
      },

      // -- structural edits -----------------------------------------
      _newId() {
        return "b" + Date.now().toString(36) + Math.floor(Math.random() * 1e4).toString(36);
      },
      addChild(type) {
        const target = this.selectedNode() || this.root;
        const slots = this.slotNames(target.type);
        if (!slots.length) {
          this.error = target.type + " accepts no children";
          return;
        }
        const slot = slots.indexOf(this.activeSlot) >= 0 ? this.activeSlot : slots[0];
        if (!target.slots) target.slots = {};
        if (!Array.isArray(target.slots[slot])) target.slots[slot] = [];
        const node = { id: this._newId(), type: type, props: {}, slots: {} };
        target.slots[slot].push(node);
        this.error = "";
        this.snapshot();
        this.select(node.id);
      },
      remove(id) {
        const hit = this._locate(id);
        if (!hit || !hit.parent) {
          this.error = "the root block cannot be removed";
          return;
        }
        hit.parent.slots[hit.slot] = hit.parent.slots[hit.slot].filter((n) => n.id !== id);
        if (this.selectedId === id) this.selectedId = null;
        this.snapshot();
      },
      move(id, dir) {
        const hit = this._locate(id);
        if (!hit || !hit.parent) return;
        const arr = hit.parent.slots[hit.slot];
        const i = arr.findIndex((n) => n.id === id);
        const j = i + dir;
        if (j < 0 || j >= arr.length) return;
        const tmp = arr[i];
        arr[i] = arr[j];
        arr[j] = tmp;
        this.snapshot();
      },
      setProp(key, value) {
        const node = this.selectedNode();
        if (!node) return;
        if (!node.props) node.props = {};
        if (value === "" || value === null) delete node.props[key];
        else node.props[key] = value;
        this.snapshot();
      },
      setPropJson(key, raw) {
        try {
          this.setProp(key, raw.trim() === "" ? "" : JSON.parse(raw));
          this.error = "";
        } catch (e) {
          this.error = key + ": invalid JSON";
        }
      },
      typeInfo() {
        const node = this.selectedNode();
        return node ? this.blockInfo(node.type) : null;
      },

      // -- raw JSON escape hatch ------------------------------------
      _syncRaw() {
        this.raw = JSON.stringify(this.root, null, 2);
      },
      editRaw(text) {
        this.raw = text;
        try {
          const parsed = text.trim() === "" ? {} : JSON.parse(text);
          this.root = parsed;
          this.error = "";
          this.snapshot();
        } catch (e) {
          this.error = "Invalid JSON";
        }
      },

      // -- history ---------------------------------------------------
      snapshot(initial) {
        const copy = JSON.parse(JSON.stringify(this.root));
        if (initial) {
          this.history = [copy];
          return;
        }
        this.history.push(copy);
        if (this.history.length > 50) this.history.shift();
        this.future = [];
        this.dirty = true;
        this._syncRaw();
      },
      undo() {
        if (this.history.length < 2) return;
        this.future.push(this.history.pop());
        this.root = JSON.parse(JSON.stringify(this.history[this.history.length - 1]));
        this.dirty = true;
        this._syncRaw();
      },
      redo() {
        if (!this.future.length) return;
        const next = this.future.pop();
        this.history.push(next);
        this.root = JSON.parse(JSON.stringify(next));
        this.dirty = true;
        this._syncRaw();
      },

      // -- persistence --------------------------------------------
      _post(url) {
        const body = new URLSearchParams({
          doc: JSON.stringify({ root: this.root }),
          revision: this.revision,
        });
        return fetch(url, {
          method: "POST",
          headers: {
            "X-CSRFToken": this._cfg.csrfToken || "",
            "Content-Type": "application/x-www-form-urlencoded",
          },
          body: body,
        });
      },
      save() {
        if (this.saving) return;
        this.saving = true;
        this.error = "";
        this._post(this._cfg.saveUrl)
          .then((r) => r.json().then((data) => ({ ok: r.ok, status: r.status, data: data })))
          .then(({ ok, status, data }) => {
            this.saving = false;
            if (ok) {
              this.revision = data.revision != null ? data.revision : this.revision;
              this.dirty = false;
              document.body.dispatchEvent(new CustomEvent("dcc:toast", { detail: "Saved" }));
              this.refreshPreview();
            } else if (status === 409) {
              this.error = "Someone else saved a newer version — reload to continue.";
              if (data.doc) {
                this.root = data.doc.root || {};
                this.raw = JSON.stringify(this.root, null, 2);
                this.revision = data.revision;
                this.dirty = false;
              }
            } else if (data.errors) {
              this.error = data.errors.map((e) => e.message).join("; ");
            } else {
              this.error = "Save failed.";
            }
          })
          .catch(() => {
            this.saving = false;
            this.error = "Save failed (network).";
          });
      },
      refreshPreview() {
        if (!this._cfg.previewUrl) return;
        this._post(this._cfg.previewUrl)
          .then((r) => r.text())
          .then((html) => {
            const target = document.getElementById("dcc-studio-preview");
            if (target) target.innerHTML = html;
          });
      },
    }));

    // ---- pointer-events reorder ------------------------------------------
    // <ul x-data="dccSortable" @dcc-reorder="...">  with children
    //   <li data-node data-index="N"> ... <button data-dcc-handle> ... </li>
    window.Alpine.data("dccSortable", () => ({
      dragIndex: null,
      init() {
        this.$el.addEventListener("pointerdown", (e) => this._start(e));
      },
      _rows() {
        return Array.from(this.$el.querySelectorAll("[data-node]"));
      },
      _start(e) {
        const handle = e.target.closest("[data-dcc-handle]");
        if (!handle) return;
        const row = handle.closest("[data-node]");
        if (!row) return;
        e.preventDefault();
        this.dragIndex = this._rows().indexOf(row);
        row.classList.add("is-dragging");
        handle.setPointerCapture(e.pointerId);

        const move = (ev) => this._over(ev, row);
        const end = (ev) => {
          handle.releasePointerCapture(e.pointerId);
          this.$el.removeEventListener("pointermove", move);
          this.$el.removeEventListener("pointerup", end);
          row.classList.remove("is-dragging");
          this._rows().forEach((r) => r.classList.remove("is-over"));
          const to = this.dragIndex;
          this.dragIndex = null;
          if (to != null) this.$dispatch("dcc-reorder", { from: this._origin, to: to });
        };
        this._origin = this.dragIndex;
        this.$el.addEventListener("pointermove", move);
        this.$el.addEventListener("pointerup", end);
      },
      _over(e, row) {
        const rows = this._rows();
        for (let i = 0; i < rows.length; i++) {
          const r = rows[i];
          if (r === row) continue;
          const box = r.getBoundingClientRect();
          const mid = box.top + box.height / 2;
          r.classList.toggle("is-over", false);
          if (e.clientY >= box.top && e.clientY <= box.bottom) {
            this.dragIndex = e.clientY < mid ? i : i + 1;
            if (this.dragIndex > this._origin) this.dragIndex--;
            r.classList.add("is-over");
          }
        }
      },
    }));
  }

  function readJson(id) {
    try {
      const el = document.getElementById(id);
      return el ? JSON.parse(el.textContent) : null;
    } catch (e) {
      return null;
    }
  }
  function titleCase(s) {
    return String(s || "").replace(/(^|[\s_-])(\w)/g, (m, p, c) => (p ? " " : "") + c.toUpperCase());
  }

  document.addEventListener("alpine:init", register);
  if (window.Alpine) register();
})();
