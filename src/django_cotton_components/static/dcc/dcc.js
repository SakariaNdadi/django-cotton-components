/*
 * django-cotton-components — small Alpine helpers.
 * Registered on alpine:init so inline x-data="dccSelect('id')" resolves.
 * No network calls: the select filters options already in the page.
 */
(function () {
  function register() {
    if (!window.Alpine) return;

    window.Alpine.data("dccSelect", (elId) => ({
      open: false,
      query: "",
      options: [],
      init() {
        const blob = document.getElementById(elId);
        try {
          this.options = blob ? JSON.parse(blob.textContent) : [];
        } catch (e) {
          this.options = [];
        }
        // options come as [[value, label], ...]
        this.options = this.options.map((o) =>
          Array.isArray(o) ? { value: String(o[0]), label: String(o[1]) } : o
        );
      },
      get searchable() {
        return this.$root.querySelector(".dcc-select__search") !== null;
      },
      get native() {
        return this.$refs.native;
      },
      toggle() {
        this.open = !this.open;
        if (this.open && this.$refs.search) {
          this.$nextTick(() => this.$refs.search.focus());
        }
      },
      close() {
        this.open = false;
        this.query = "";
      },
      filtered() {
        const q = this.query.toLowerCase();
        return q
          ? this.options.filter((o) => o.label.toLowerCase().includes(q))
          : this.options;
      },
      selectedValues() {
        return Array.from(this.native.selectedOptions).map((o) => o.value);
      },
      isSelected(value) {
        return this.selectedValues().includes(String(value));
      },
      choose(value) {
        const opt = Array.from(this.native.options).find(
          (o) => o.value === String(value)
        );
        if (!opt) return;
        if (this.native.multiple) {
          opt.selected = !opt.selected;
        } else {
          this.native.value = String(value);
          this.close();
        }
        this.native.dispatchEvent(new Event("change", { bubbles: true }));
      },
      syncFromNative() {},
      triggerLabel() {
        const picked = this.selectedValues();
        if (!picked.length) return "";
        return this.options
          .filter((o) => picked.includes(o.value))
          .map((o) => o.label)
          .join(", ");
      },
    }));

    // Client-side table: rows are server-rendered <tr data-dcc-pk>. This
    // component filters/sorts/paginates by reordering and x-show-ing those
    // real nodes, so rich cells and row actions keep working. Zero requests.
    window.Alpine.data("dccTable", (configId) => ({
      meta: {},            // pk -> {"0": text, "1": text, ...}
      order: [],           // pk order as delivered by the server
      search: "",
      filters: {},
      sortIndex: null,
      sortDir: 1,
      page: 1,
      perPage: 25,
      matchCount: 0,
      _visible: new Set(),
      init() {
        try {
          const el = document.getElementById(configId);
          const cfg = el ? JSON.parse(el.textContent) : {};
          this.perPage = cfg.perPage || 25;
          (cfg.rows || []).forEach((r) => {
            this.order.push(r._pk);
            this.meta[r._pk] = r;
          });
        } catch (e) {
          /* keep empty */
        }
        this.$watch("search", () => this.recompute());
        this.$watch("filters", () => this.recompute());
        this.recompute();
      },
      setFilter(name, value) {
        if (value === "" || value == null) this.filters = omit(this.filters, name);
        else this.filters = { ...this.filters, [name]: String(value) };
        this.page = 1;
      },
      _matches(pk) {
        const row = this.meta[pk] || {};
        const q = this.search.trim().toLowerCase();
        if (q) {
          const hay = Object.keys(row)
            .filter((k) => k !== "_pk")
            .map((k) => String(row[k]).toLowerCase())
            .join(" ");
          if (!hay.includes(q)) return false;
        }
        // filters match against any column whose text equals the value
        for (const value of Object.values(this.filters)) {
          const v = value.toLowerCase();
          const hit = Object.keys(row).some(
            (k) => k !== "_pk" && String(row[k]).toLowerCase() === v
          );
          if (!hit) return false;
        }
        return true;
      },
      _sorted(pks) {
        if (this.sortIndex === null) return pks;
        const idx = String(this.sortIndex);
        return [...pks].sort((a, b) => {
          const av = (this.meta[a] || {})[idx] ?? "";
          const bv = (this.meta[b] || {})[idx] ?? "";
          const an = parseFloat(av);
          const bn = parseFloat(bv);
          const cmp =
            !isNaN(an) && !isNaN(bn)
              ? an - bn
              : String(av).localeCompare(String(bv), undefined, { sensitivity: "base" });
          return cmp * this.sortDir;
        });
      },
      recompute() {
        const kept = this._sorted(this.order.filter((pk) => this._matches(pk)));
        this.matchCount = kept.length;
        if (this.page > this.totalPages()) this.page = this.totalPages();
        const start = (this.page - 1) * this.perPage;
        const pagep = kept.slice(start, start + this.perPage);
        this._visible = new Set(pagep);
        // reorder DOM to the sorted page order
        const body = this.$refs.body;
        if (body) {
          pagep.forEach((pk) => {
            const tr = body.querySelector(`[data-dcc-pk="${cssEscape(pk)}"]`);
            if (tr) body.appendChild(tr);
          });
        }
      },
      isVisible(pk) {
        return this._visible.has(String(pk));
      },
      totalPages() {
        const n = this.order.filter((pk) => this._matches(pk)).length;
        return Math.max(1, Math.ceil(n / this.perPage));
      },
      sortBy(index) {
        if (this.sortIndex === index) this.sortDir *= -1;
        else {
          this.sortIndex = index;
          this.sortDir = 1;
        }
        this.page = 1;
        this.recompute();
      },
      sortCue(index) {
        if (this.sortIndex !== index) return "";
        return this.sortDir === 1 ? "▲" : "▼";
      },
      nextPage() {
        if (this.page < this.totalPages()) {
          this.page++;
          this.recompute();
        }
      },
      prevPage() {
        if (this.page > 1) {
          this.page--;
          this.recompute();
        }
      },
    }));

    function omit(obj, key) {
      const copy = { ...obj };
      delete copy[key];
      return copy;
    }
    function cssEscape(value) {
      return String(value).replace(/["\\]/g, "\\$&");
    }

    window.Alpine.data("dccUpload", () => ({
      preview: "",
      show(event) {
        const file = event.target.files && event.target.files[0];
        if (file && file.type.startsWith("image/")) {
          this.preview = URL.createObjectURL(file);
        } else {
          this.preview = "";
        }
      },
    }));
  }

  document.addEventListener("alpine:init", register);
  if (window.Alpine) register();

  // Toasts: the action endpoint fires HX-Trigger {"dcc:toast": "..."} which
  // htmx re-emits as a window event. Render it if a container is present.
  function toast(message) {
    let host = document.getElementById("dcc-toasts");
    if (!host) {
      host = document.createElement("div");
      host.id = "dcc-toasts";
      host.className = "dcc-toasts";
      document.body.appendChild(host);
    }
    const el = document.createElement("div");
    el.className = "dcc-toast";
    el.setAttribute("role", "status");
    el.textContent = typeof message === "string" ? message : (message && message.value) || "Done";
    host.appendChild(el);
    setTimeout(() => el.classList.add("is-leaving"), 3200);
    setTimeout(() => el.remove(), 3600);
  }
  document.body.addEventListener("dcc:toast", (e) => toast(e.detail));
  // dcc:refresh is handled by htmx: the table shell carries a hidden element
  // with hx-trigger="dcc:refresh from:body" that re-fetches its content.
})();
