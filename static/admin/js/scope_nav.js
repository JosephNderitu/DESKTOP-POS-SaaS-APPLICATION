// Hides platform-only nav elements (Clients topmenu link, Client search box)
// when the admin is being viewed on a tenant subdomain rather than the base
// platform domain. Purely cosmetic — Client/Domain/PlatformAuditLog aren't
// registered on the tenant admin site at all, so these links 404 harmlessly
// even without this script; this just keeps them from being visible noise.
(function () {
    const isTenantSubdomain = window.location.hostname !== "localhost" && window.location.hostname !== "127.0.0.1";
    if (!isTenantSubdomain) return;

    document.querySelectorAll('a[href*="/tenants/client/"]').forEach(function (link) {
        const menuItem = link.closest("li") || link;
        menuItem.style.display = "none";
    });

    document.querySelectorAll('form[action*="/tenants/client/"]').forEach(function (form) {
        form.style.display = "none";
    });
})();