/*
 * django-control-components — studio builder runtime.
 * Loaded only by {% dcc_studio_assets %}, never on a normal panel page.
 *
 * Three Alpine components:
 *   dccStudioDoc(bootId)   the edited document + dirty/undo/redo + save
 *   dccSortable            pointer-events reorder of a flat <ul> of [data-node]
 *   dccInspector           renders a node's editable fields from the palette JSON
 */
(function () {
  function register() {
    if (!window.Alpine) return;

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
