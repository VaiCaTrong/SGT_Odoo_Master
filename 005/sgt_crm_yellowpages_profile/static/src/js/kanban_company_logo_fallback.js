/** CRM-005 Update_035: revert to the building icon if a remote/uploaded logo fails. */
(function () {
    "use strict";
    if (window.__sgtCRM005KanbanLogoErrorHandler) return;
    window.__sgtCRM005KanbanLogoErrorHandler = true;

    // Capturing image errors also handles cards added after drag/drop/filter/paging.
    document.addEventListener("error", function (event) {
        const img = event.target;
        if (img instanceof HTMLImageElement &&
            img.classList.contains("sgt_crm005_kanban_logo_img")) {
            img.classList.add("sgt_crm005_broken");
        }
    }, true);
})();
