/*
 * Surfaces server-side row truncation on the pivot explorers.
 *
 * report/pivot_limits.py caps a pivot payload at MAX_PIVOT_ROWS and reports
 * that fact in the X-Horilla-Pivot-Truncated response header. The explorer
 * pages fetch with $.getJSON, which discards headers, and nothing read it --
 * so past the cap the pivot presented the sum of the first N rows as if it
 * were the complete total. On payroll data that is silently wrong money.
 *
 * Rather than edit ten-odd fetch sites across seven near-identical
 * templates, this hooks jQuery's global ajaxComplete once and renders a
 * banner whenever a pivot response comes back capped.
 */
(function () {
    "use strict";

    if (typeof jQuery === "undefined") {
        return;
    }

    var $ = jQuery;
    var BANNER_ID = "pivot-truncation-notice";

    function bannerText(limit) {
        var shown = limit ? Number(limit).toLocaleString() : "";
        // Deliberately explicit that totals are affected, not just the row
        // list -- an incomplete pivot total is the actual hazard here.
        return shown
            ? "Showing the first " +
                  shown +
                  " rows. Totals below cover only these rows — narrow the " +
                  "filters, or use Standard Reports for a complete figure."
            : "This result was truncated. Totals below are incomplete — " +
                  "narrow the filters, or use Standard Reports for a " +
                  "complete figure.";
    }

    function removeBanner() {
        var existing = document.getElementById(BANNER_ID);
        if (existing && existing.parentNode) {
            existing.parentNode.removeChild(existing);
        }
    }

    function showBanner(limit) {
        removeBanner();

        // Anchor above the pivot itself so it cannot be scrolled away from
        // the numbers it qualifies.
        var anchor =
            document.getElementById("pivot-container") ||
            document.querySelector(".pivot-wrapper");
        if (!anchor || !anchor.parentNode) {
            return;
        }

        var banner = document.createElement("div");
        banner.id = BANNER_ID;
        banner.setAttribute("role", "status");
        banner.className = "oh-alert oh-alert--warning";
        banner.style.cssText =
            "margin:0 0 12px;padding:10px 14px;border-radius:4px;" +
            "background:#FFF4CE;border:1px solid #E8B84B;color:#5C4413;" +
            "font-size:13px;line-height:1.5;";
        banner.textContent = bannerText(limit);
        anchor.parentNode.insertBefore(banner, anchor);
    }

    $(document).ajaxComplete(function (_event, xhr, settings) {
        var url = (settings && settings.url) || "";
        if (url.indexOf("-pivot") === -1) {
            return;
        }
        var truncated;
        try {
            truncated = xhr.getResponseHeader("X-Horilla-Pivot-Truncated");
        } catch (err) {
            // Some transports throw rather than returning null.
            return;
        }
        if (truncated === "1") {
            var limit = null;
            try {
                limit = xhr.getResponseHeader("X-Horilla-Pivot-Limit");
            } catch (err) {
                limit = null;
            }
            showBanner(limit);
        } else {
            // A subsequent, narrower query fits: retract the warning.
            removeBanner();
        }
    });
})();
