/* A readout of the numbers, on the device that actually has the bug.
 *
 *     …/myArtisticProject/?measure=1
 *
 * TEMPORARY, AND GATED. It does nothing at all unless `measure` is in
 * the query string, so no visitor ever sees it. Delete this file and
 * the one line in templates/index.html when the question is answered.
 *
 * WHY IT EXISTS. Six fixes to the open patchwork were verified in
 * headless Chrome and in an iPhone simulator, and every one of them was
 * reported straight back as still broken on the real phone. Every
 * number used to justify those fixes came from a machine that does not
 * have the fault. This prints, on the phone, the handful of values that
 * decide it — and if the numbers here disagree with the ones measured
 * in the simulator, the disagreement IS the bug.
 */
(function () {
  if (!/[?&]measure/.test(location.search)) return;

  var box = document.createElement("div");
  box.setAttribute("id", "measure");
  document.documentElement.appendChild(box);

  function px(unit) {
    var probe = document.createElement("div");
    probe.style.cssText = "position:absolute;visibility:hidden;width:1px;height:100" + unit;
    document.body.appendChild(probe);
    var h = Math.round(probe.getBoundingClientRect().height);
    probe.remove();
    return h;
  }

  /* Anything between the photograph and the viewport that clips it, or
   * that captures `position: fixed` — the two ways an overlay stops
   * being the screen. */
  function chain(el) {
    var out = [], a = el && el.parentElement;
    while (a && a !== document.documentElement) {
      var s = getComputedStyle(a);
      var flags = [];
      if (s.overflow !== "visible") flags.push("clip:" + s.overflow);
      if (s.transform !== "none") flags.push("transform");
      if (s.filter !== "none") flags.push("filter");
      if (s.webkitBackdropFilter && s.webkitBackdropFilter !== "none") flags.push("backdrop");
      if ((s.willChange || "").indexOf("transform") >= 0) flags.push("will-change");
      if ((s.contain || "").indexOf("paint") >= 0) flags.push("contain");
      if (flags.length) {
        out.push(((a.className || "").toString().split(" ")[0] || a.tagName)
                 + "[" + flags.join(",") + "]");
      }
      if (s.position === "fixed") break;
      a = a.parentElement;
    }
    return out.join(" ") || "nothing";
  }

  function line(label, value) { return label + " " + value; }

  function read() {
    var vv = window.visualViewport;
    var front = document.querySelector(".group[open] > .group-front")
             || document.querySelector(".shots[open] > .reel");
    var img = document.querySelector(".group[open] .group-front .fridge > .slot-1 img");
    var rows = [
      line("screen  ", screen.width + "x" + screen.height + "  dpr" + (window.devicePixelRatio || 1)),
      line("inner   ", window.innerWidth + "x" + window.innerHeight),
      line("visual  ", vv ? Math.round(vv.width) + "x" + Math.round(vv.height)
                            + " off" + Math.round(vv.offsetTop) : "none"),
      line("units   ", "svh " + px("svh") + "  lvh " + px("lvh") + "  dvh " + px("dvh")),
    ];
    if (front) {
      var b = front.getBoundingClientRect();
      var cs = getComputedStyle(front);
      rows.push(line("FRONT   ", Math.round(b.width) + "x" + Math.round(b.height)
        + " top" + Math.round(b.top) + " bot" + Math.round(b.bottom)));
      rows.push(line("  css   ", "h=" + cs.height + " pos=" + cs.position
        + " bg=" + (cs.backgroundColor || "").replace(/\s/g, "")));
    } else {
      rows.push("FRONT    nothing open — tap a patchwork");
    }
    if (img) {
      var i = img.getBoundingClientRect();
      rows.push(line("PHOTO   ", Math.round(i.width) + "x" + Math.round(i.height)
        + " top" + Math.round(i.top) + " bot" + Math.round(i.bottom)));
      rows.push(line("  cutBy ", chain(img)));
    }
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
