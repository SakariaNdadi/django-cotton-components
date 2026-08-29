/*
 * django-cotton-components — small Alpine helpers.
 * Registered on alpine:init so inline x-data="dccSelect('id')" resolves.
 * No network calls: the select filters options already in the page.
 */
(function () {
  // Widget renderer registry. A charting library registers a function that
  // draws into a mount node given the widget's JSON payload. Defined before
  // alpine:init so a third-party <script> can call it at any time:
  //   window.dccWidgets.register("apexcharts", (node, payload) => { ... })
  window.dccWidgets = window.dccWidgets || {
    renderers: {},
    register: function (name, fn) {
      this.renderers[name] = fn;
    },
  };

  // Chart.js is the built-in renderer. It may `defer` in after Alpine, so
  // register lazily on first use rather than at alpine:init.
  function ensureChartjsRenderer() {
    if (!window.dccWidgets.renderers.chartjs && window.Chart) {
      window.dccWidgets.register("chartjs", function (canvas, payload) {
        return new window.Chart(canvas, {
          type: payload.type,
          data: payload.data,
          options: payload.options,
        });
      });
    }
  }

  function register() {
    if (!window.Alpine) return;

    // Reactive mirror of a form's field values, so `.visible_when(...)` (compiled
    // to x-show="$dccField('name') == ...") re-evaluates when a sibling changes.
    function fieldValue(el) {
      if (el.type === "checkbox") return el.checked;
      if (el.multiple) return Array.from(el.selectedOptions).map((o) => o.value);
      return el.value;
    }
    window.Alpine.data("dccForm", () => ({
      values: {},
      init() {
        const seen = new Set();
        this.$root.querySelectorAll("[name]").forEach((el) => {
          if (seen.has(el.name)) return;
          seen.add(el.name);
          this.values[el.name] = fieldValue(el);
        });
        this.$root.addEventListener("input", (e) => {
          if (e.target.name) this.values[e.target.name] = fieldValue(e.target);
        });
        this.$root.addEventListener("change", (e) => {
          if (e.target.name) this.values[e.target.name] = fieldValue(e.target);
        });
      },
    }));
    window.Alpine.magic("dccField", (el) => (name) => {
      const host = el.closest(".dcc-form");
      if (!host) return undefined;
      const data = window.Alpine.$data(host);
      return data && data.values ? data.values[name] : undefined;
    });

    // Searchable/reactive select. Wraps a real <select x-ref="native"> (which
    // still submits and works with JS off). `selected` is reactive state — the
    // trigger label and option highlight read it, so picking an option updates
    // the UI immediately; every change is mirrored onto the native <select>.
    window.Alpine.data("dccSelect", (elId) => ({
      open: false,
      query: "",
      options: [],
      selected: [],
      multiple: false,
      searchable: false,
      init() {
        const blob = document.getElementById(elId);
        try {
          this.options = (blob ? JSON.parse(blob.textContent) : []).map((o) =>
            Array.isArray(o) ? { value: String(o[0]), label: String(o[1]) } : o
          );
        } catch (e) {
          this.options = [];
        }
        const ds = this.$root.dataset || {};
        this.multiple = ds.multiple === "1" || !!this.native.multiple;
        this.searchable = ds.searchable === "1";
        this.selected = Array.from(this.native.selectedOptions).map((o) => o.value);
        // keep in sync if something else writes to the native select
        this.native.addEventListener("change", () => {
          this.selected = Array.from(this.native.selectedOptions).map((o) => o.value);
        });
      },
      get native() {
        return this.$refs.native;
      },
      toggle() {
        this.open = !this.open;
        if (this.open && this.searchable) {
          this.$nextTick(() => this.$refs.search && this.$refs.search.focus());
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
      isSelected(value) {
        return this.selected.includes(String(value));
      },
      choose(value) {
        const v = String(value);
        if (this.multiple) {
          this.selected = this.isSelected(v)
            ? this.selected.filter((x) => x !== v)
            : [...this.selected, v];
        } else {
          this.selected = [v];
          this.close();
        }
        Array.from(this.native.options).forEach((o) => {
          o.selected = this.selected.includes(o.value);
        });
        this.native.dispatchEvent(new Event("change", { bubbles: true }));
      },
      triggerLabel() {
        if (!this.selected.length) return "";
        return this.options
          .filter((o) => this.selected.includes(o.value))
          .map((o) => o.label)
          .join(", ");
      },
    }));

    // Row selection for bulk actions. Shared by the client-side table engine
    // (dccTable) and by dccBulk (server-side tables). `selected` is an array of
    // pk strings bound to the row checkboxes via x-model; the bulk trigger reads
    // the checked boxes straight from the DOM through hx-include.
    //
    // A module-level cache keyed by table id keeps the selection alive across
    // htmx content swaps (a client-mode filter re-creates the whole dccTable).
    const _selCache = Object.create(null);
    // A mutating action fires dcc:refresh (htmx re-emits it on <body>); every
    // table then drops any stale selection. One listener, bound once.
    let _refreshBound = false;
    function bindGlobalRefresh() {
      if (_refreshBound) return;
      _refreshBound = true;
      document.body.addEventListener("dcc:refresh", () => {
        for (const key in _selCache) delete _selCache[key];
      });
    }

    // NOTE: `selectedCount` / `allSelected` are METHODS, not getters — this
    // object is spread into the host components (`{ ...selectionState() }`) and
    // object spread would freeze a getter to its one-time value. Templates call
    // `selectedCount()` / `allSelected()`.
    function selectionState() {
      return {
        selected: [],
        selectAll: false, // "every row matching the filter", not just this page
        _selId: "",
        // Restore any cached selection and start mirroring changes back into the
        // cache. Called from each host's init() once $root/refs are live.
        _bindSelection(id) {
          this._selId = id;
          bindGlobalRefresh();
          const cached = _selCache[id];
          this.selected = cached ? cached.selected.slice() : [];
          this.selectAll = cached ? cached.selectAll : false;
          const save = () => {
            _selCache[id] = {
              selected: this.selected.slice(),
              selectAll: this.selectAll,
            };
          };
          this.$watch("selected", save);
          this.$watch("selectAll", save);
        },
        rowCount() {
          return this.$root ? this.$root.querySelectorAll("[data-dcc-bulk]").length : 0;
        },
        selectedCount() {
          return this.selected.length;
        },
        allSelected() {
          const n = this.rowCount();
          return n > 0 && this.selected.length >= n;
        },
        toggleAll(checked) {
          if (checked) {
            this.selected = Array.from(
              this.$root.querySelectorAll("[data-dcc-bulk]")
            ).map((el) => el.value);
          } else {
            this.selected = [];
            this.selectAll = false;
          }
        },
        clearSelection() {
          this.selected = [];
          this.selectAll = false;
        },
      };
    }

    window.Alpine.data("dccBulk", () => ({
      ...selectionState(),
      init() {
        this._bindSelection(this.$root.id);
      },
    }));

    // Client-side table: rows are server-rendered <tr data-dcc-pk>. This
    // component filters/sorts/paginates by reordering and x-show-ing those
    // real nodes, so rich cells and row actions keep working. Zero requests.
    window.Alpine.data("dccTable", (configId) => ({
      ...selectionState(),
      meta: {},            // pk -> {"0": text, "1": text, ...}
      order: [],           // pk order as delivered by the server
      search: "",
      sortIndex: null,
      sortDir: 1,
      page: 1,
      perPage: 25,
      limit: 25,           // infinite-scroll: rows shown so far
      infiniteScroll: false,
      matchCount: 0,
      _visible: new Set(),
      init() {
        try {
          const el = document.getElementById(configId);
          const cfg = el ? JSON.parse(el.textContent) : {};
          this.perPage = cfg.perPage || 25;
          this.limit = this.perPage;
          this.infiniteScroll = !!cfg.infiniteScroll;
          (cfg.rows || []).forEach((r) => {
            this.order.push(r._pk);
            this.meta[r._pk] = r;
          });
        } catch (e) {
          /* keep empty */
        }
        this._bindSelection(configId.replace(/-config$/, ""));
        this.$watch("search", () => {
          this.page = 1;
          this.limit = this.perPage;
          this.recompute();
        });
        this.$watch("perPage", () => {
          this.page = 1;
          this.limit = this.perPage;
          this.recompute();
        });
        if (this.infiniteScroll) this._observeSentinel();
        this.recompute();
      },
      _observeSentinel() {
        const sentinel = this.$root.querySelector("[data-dcc-sentinel]");
        if (!sentinel || !window.IntersectionObserver) return;
        new IntersectionObserver((entries) => {
          if (entries.some((e) => e.isIntersecting)) this.loadMore();
        }).observe(sentinel);
      },
      loadMore() {
        if (this.limit < this.matchCount) {
          this.limit += this.perPage;
          this.recompute();
        }
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
        let pagep;
        if (this.infiniteScroll) {
          pagep = kept.slice(0, this.limit);
        } else {
          if (this.page > this.totalPages()) this.page = this.totalPages();
          const start = (this.page - 1) * this.perPage;
          pagep = kept.slice(start, start + this.perPage);
        }
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
        return Math.max(1, Math.ceil(this.matchCount / this.perPage));
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

    function cssEscape(value) {
      return String(value).replace(/["\\]/g, "\\$&");
    }

    // Dashboard chart widget. Reads a json_script payload (#<id>-data) and hands
    // it to the registered renderer for payload.library, drawing into
    // <canvas x-ref="canvas">. htmx swaps the whole #<id>-content fragment on
    // refresh/poll, so init() re-runs on fresh nodes; destroy() tears the
    // instance down so Chart.js does not leak the canvas.
    window.Alpine.data("dccChart", (elId) => ({
      _instance: null,
      init() {
        this._draw();
      },
      destroy() {
        if (this._instance && typeof this._instance.destroy === "function") {
          this._instance.destroy();
        }
        this._instance = null;
      },
      _payload() {
        try {
          const el = document.getElementById(elId);
          return el ? JSON.parse(el.textContent) : null;
        } catch (e) {
          return null;
        }
      },
      _draw(attempt) {
        attempt = attempt || 0;
        const payload = this._payload();
        const canvas = this.$refs.canvas;
        if (!payload || !canvas) return;
        ensureChartjsRenderer();
        const renderer = window.dccWidgets.renderers[payload.library];
        if (!renderer) {
          // Chart.js may still be loading (defer, after Alpine). Retry briefly.
          if (payload.library === "chartjs" && attempt < 50) {
            setTimeout(() => this._draw(attempt + 1), 100);
          }
          return;
        }
        // A stale Chart.js instance may still own this canvas after a swap.
        if (window.Chart && typeof window.Chart.getChart === "function") {
          const prior = window.Chart.getChart(canvas);
          if (prior) prior.destroy();
        }
        this.destroy();
        this._instance = renderer(canvas, payload) || null;
      },
    }));

    // Panel shell: mobile nav drawer + a persisted colour-theme toggle that
    // writes data-theme onto <html> (dcc.css keys its dark palette off it).
    window.Alpine.data("dccShell", () => ({
      navOpen: false,
      theme: "auto",
      init() {
        try {
          this.theme = localStorage.getItem("dcc-theme") || "auto";
        } catch (e) {
          this.theme = "auto";
        }
        this.applyTheme();
        this.$watch("navOpen", (open) => {
          document.body.classList.toggle("dcc-no-scroll", open);
        });
      },
      applyTheme() {
        const root = document.documentElement;
        if (this.theme === "auto") root.removeAttribute("data-theme");
        else root.setAttribute("data-theme", this.theme);
      },
      cycleTheme() {
        const order = ["auto", "light", "dark"];
        this.theme = order[(order.indexOf(this.theme) + 1) % order.length];
        try {
          localStorage.setItem("dcc-theme", this.theme);
        } catch (e) {
          /* private mode: keep the in-memory value */
        }
        this.applyTheme();
      },
      themeLabel() {
        return { auto: "◐", light: "☀", dark: "☾" }[this.theme] || "◐";
      },
    }));

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

  // -- clickable rows -------------------------------------------------------
  // A row carries data-dcc-href (navigate) or data-dcc-action (htmx GET, e.g.
  // opening a modal). Delegated + guarded so buttons/inputs inside the row keep
  // working and text selection never triggers a navigation. Survives htmx swaps.
  var ROW_INTERACTIVE = "a,button,input,select,textarea,label,.dcc-menu,[data-dcc-bulk]";
  function rowTarget(el) {
    return el.closest("[data-dcc-href],[data-dcc-action]");
  }
  document.addEventListener("click", function (e) {
    var row = rowTarget(e.target);
    if (!row || e.defaultPrevented) return;
    if (e.target.closest(ROW_INTERACTIVE)) return;
    if (window.getSelection && String(window.getSelection()).length) return;
    var href = row.getAttribute("data-dcc-href");
    if (href) {
      if (e.metaKey || e.ctrlKey) window.open(href, "_blank");
      else window.location.assign(href);
      return;
    }
    var url = row.getAttribute("data-dcc-action");
    if (url && window.htmx) {
      window.htmx.ajax("GET", url, {
        target: row.getAttribute("data-dcc-action-target") || "body",
        swap: row.getAttribute("data-dcc-action-swap") || "innerHTML",
      });
    }
  });
  document.addEventListener("keydown", function (e) {
    if (e.key !== "Enter") return;
    var row = rowTarget(e.target);
    if (row && e.target === row) {
      e.preventDefault();
      row.click();
    }
  });

  // -- hover preview card --------------------------------------------------
  // A row with a <template class="dcc-row-preview"> shows its content in a
  // floating card after a short hover.
  var previewCard = null;
  var previewTimer = null;
  function hidePreview() {
    if (previewTimer) {
      clearTimeout(previewTimer);
      previewTimer = null;
    }
    if (previewCard) {
      previewCard.remove();
      previewCard = null;
    }
  }
  function showPreview(row) {
    var tpl = row.querySelector("template.dcc-row-preview");
    if (!tpl) return;
    hidePreview();
    previewCard = document.createElement("div");
    previewCard.className = "dcc-row-preview-card";
    previewCard.appendChild(tpl.content.cloneNode(true));
    document.body.appendChild(previewCard);
    var r = row.getBoundingClientRect();
    var c = previewCard.getBoundingClientRect();
    var top = window.scrollY + r.bottom + 6;
    if (r.bottom + c.height + 16 > window.innerHeight && r.top - c.height - 6 > 0) {
      top = window.scrollY + r.top - c.height - 6;
    }
    var left = Math.min(
      window.scrollX + r.left,
      window.scrollX + window.innerWidth - c.width - 12
    );
    previewCard.style.top = top + "px";
    previewCard.style.left = Math.max(8, left) + "px";
  }
  document.addEventListener("mouseover", function (e) {
    var row = e.target.closest("[data-dcc-row]");
    if (!row || !row.querySelector("template.dcc-row-preview")) return;
    if (previewTimer) clearTimeout(previewTimer);
    previewTimer = setTimeout(function () {
      showPreview(row);
    }, 350);
  });
  document.addEventListener("mouseout", function (e) {
    var row = e.target.closest("[data-dcc-row]");
    if (!row) return;
    if (!e.relatedTarget || !row.contains(e.relatedTarget)) hidePreview();
  });
  document.addEventListener("scroll", hidePreview, true);
  document.body.addEventListener("dcc:refresh", hidePreview);
})();
