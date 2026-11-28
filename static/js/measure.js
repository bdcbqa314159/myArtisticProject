/* A readout of the numbers, on the device that actually has the bug.
 *
 *     …/myArtisticProject/?measure=1
 *
 * TEMPORARY, AND GATED. Nothing happens unless `measure` is in the
 * query string. Delete this file, the line in templates/index.html and
 * the #measure block in site.css when the question is answered.
 *
 * WHAT THE FIRST VERSION ESTABLISHED, from the real phone:
 *
 *   FRONT  393x793 top0 bot793        — identical with the toolbar in or out
 *   PHOTO  393x1193 top-200 bot993    — identical, and 352px past the visible area
 *   inner  641 (bar shown) / 749 (hidden)
 *
 * So the geometry is right and the same in both states, while the
 * screen shows the photograph stopping short. Layout and paint
 * disagree, which means the cut happens when the pixels are drawn —
 * and a bounding box cannot see that, which is what hid an
 * `overflow: clip` for two releases.
 *
 * SO THIS ASKS THE SCREEN INSTEAD. `elementFromPoint` returns what is
 * actually painted and hit-testable at a coordinate. Sampling down the
 * viewport answers the only question left: at the bottom of the
 * screen, is the photograph there or is the page there? And the
 * ancestor walk no longer stops at the fixed element — if something
 * ABOVE the overlay is capturing it, that is exactly where it lives —
 * and it now looks for `clip-path` and `mask`, which cut paint while
 * leaving the box untouched.
 */
(function () {
  if (!/[?&]measure/.test(location.search)) return;

  var box = document.createElement("div");
  box.setAttribute("id", "measure");
  document.documentElement.appendChild(box);

  function px(unit) {
    var p = document.createElement("div");
    p.style.cssText = "position:absolute;visibility:hidden;width:1px;height:100" + unit;
    document.body.appendChild(p);
    var h = Math.round(p.getBoundingClientRect().height);
    p.remove();
    return h;
  }

  function name(el) {
    if (!el) return "none";
    var c = (el.className || "").toString().trim().split(/\s+/)[0];
    return el.tagName.toLowerCase() + (c ? "." + c : "");
  }

  /* Everything between the photograph and the root that could move or
   * cut it. No stopping at the fixed element this time. */
  function chain(el) {
    var out = [], a = el && el.parentElement, depth = 0;
    while (a && depth < 40) {
      var s = getComputedStyle(a), f = [];
      if (s.overflow !== "visible") f.push("ovf:" + s.overflow);
      if (s.clipPath && s.clipPath !== "none") f.push("clip-path");
      if ((s.webkitMaskImage && s.webkitMaskImage !== "none")
          || (s.maskImage && s.maskImage !== "none")) f.push("mask");
      if (s.transform !== "none") f.push("transform");
      if (s.filter !== "none") f.push("filter");
      if ((s.contain || "").indexOf("paint") >= 0) f.push("contain");
      if ((s.willChange || "").indexOf("transform") >= 0) f.push("will-change");
      if (s.perspective !== "none") f.push("perspective");
      if (s.position === "fixed") f.push("FIXED");
      if (f.length) out.push(name(a) + "[" + f.join(",") + "]");
      a = a.parentElement;
      depth += 1;
    }
    return out.join(" ") || "nothing";
  }

  /* WHAT IS ACTUALLY ON THE SCREEN, at five heights down the visible
   * viewport. This is the question the boxes cannot answer. */
  function painted() {
    var w = Math.round(window.innerWidth / 2), h = window.innerHeight, out = [];
    [0.08, 0.3, 0.6, 0.88, 0.98].forEach(function (f) {
      var y = Math.min(h - 2, Math.round(h * f));
      out.push(Math.round(f * 100) + "%:" + name(document.elementFromPoint(w, y)));
    });
    return out.join(" ");
  }

  function read() {
    var vv = window.visualViewport;
    var front = document.querySelector(".group[open] > .group-front");
    var img = document.querySelector(".group[open] .group-front .fridge > .slot-1 img");
    var rows = [
      "inner   " + window.innerWidth + "x" + window.innerHeight
        + "   visual " + (vv ? Math.round(vv.height) + " off" + Math.round(vv.offsetTop) : "-"),
      "units   svh " + px("svh") + "  lvh " + px("lvh") + "  dvh " + px("dvh"),
    ];
    if (front) {
      var b = front.getBoundingClientRect();
      rows.push("FRONT   " + Math.round(b.width) + "x" + Math.round(b.height)
        + " top" + Math.round(b.top) + " bot" + Math.round(b.bottom));
    }
    if (img) {
      var i = img.getBoundingClientRect();
      rows.push("PHOTO   " + Math.round(i.width) + "x" + Math.round(i.height)
        + " top" + Math.round(i.top) + " bot" + Math.round(i.bottom));
      rows.push("above   " + chain(img));
    }
    rows.push("ON SCREEN");
    rows.push("  " + painted());
    box.textContent = rows.join("\n");
  }

  read();
  setInterval(read, 400);
  addEventListener("scroll", read, { passive: true });
  addEventListener("resize", read);
  if (window.visualViewport) {
    visualViewport.addEventListener("resize", read);
    visualViewport.addEventListener("scroll", read);
  }
})();
