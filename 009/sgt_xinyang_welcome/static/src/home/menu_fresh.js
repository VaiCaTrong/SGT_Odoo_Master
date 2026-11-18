/** @odoo-module **/
// Update_033: always show the CURRENT app menu (Home included) when a backend page opens.
//
// Odoo keeps a copy of the app menu in the browser (localStorage "webclient_menus"), draws the page from that copy
// first and only then asks the server for the real menu. When the copy is old (made before Home existed, or by
// another account in the same browser) the app menu opens without Home and, if it is opened at that moment, stays
// that way until the page is reloaded. Dropping the copy here, before Odoo reads it, makes Odoo wait the few
// milliseconds for the server's menu (the page has already started that request) and draw it once, correctly.
// Nothing else is touched: the server still sends exactly the menus the signed-in user may see.
try {
    window.localStorage.removeItem("webclient_menus");
} catch {
    /* storage may be blocked: Odoo then loads the menu from the server anyway */
}
