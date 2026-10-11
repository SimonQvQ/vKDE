// vKDE public preset: creates a new layout without activity IDs or personal paths.
var topStyle = __TOP__;
var bottomStyle = __BOTTOM__;
var pins = __PINS__;
function cfg(w, group, values) {
    w.currentConfigGroup = group;
    for (var key in values) w.writeConfig(key, values[key]);
    w.reloadConfig();
}
function colorize(panel, style) {
    var w = panel.addWidget('luisbocanegra.panel.colorizer');
    cfg(w, ['General'], {globalSettings: JSON.stringify(style), isEnabled: true,
        hideWidget: false, hiddenWidgets: '{"widgets":[]}',
        configurationOverrides: '{"overrides":{},"associations":[]}', presetAutoloading: '{}'});
}
// Remove panels only. Desktop applets and wallpapers are retained.
panels().forEach(function(p) { p.remove(); });
var top = new Panel();
top.location = 'top'; top.height = 40; top.hiding = 'none'; top.floating = true;
cfg(top.addWidget('org.kde.plasma.kickoff'), ['General'], {icon: 'start-here-kde-symbolic'});
cfg(top.addWidget('org.kde.plasma.icontasks'), ['General'], {launchers: '', showOnlyCurrentDesktop: true});
top.addWidget('org.kde.plasma.windowlist');
top.addWidget('org.kde.plasma.appmenu');
top.addWidget('org.kde.plasma.panelspacer');
cfg(top.addWidget('org.kde.plasma.digitalclock'), ['Appearance'], {use24hFormat: 2, showDate: false});
top.addWidget('org.kde.plasma.panelspacer');
colorize(top, topStyle);
top.addWidget('org.kde.plasma.systemtray');
var dock = new Panel();
dock.location = 'bottom'; dock.height = 64; dock.floating = true;
dock.alignment = 'center'; dock.lengthMode = 'fit'; dock.hiding = 'dodgewindows';
cfg(dock.addWidget('org.kde.plasma.icontasks'), ['General'], {launchers: pins.join(','), showOnlyCurrentDesktop: true});
colorize(dock, bottomStyle);
desktops().forEach(function(d) {
    if (!d.widgets('org.simonqvq.redmiclock').length) {
        var c = d.addWidget('org.simonqvq.redmiclock');
        c.geometry = {x: 40, y: 70, width: 400, height: 250};
    }
    if (!d.widgets('org.kde.plasma.systemmonitor.memory').length) {
        var m = d.addWidget('org.kde.plasma.systemmonitor.memory');
        m.geometry = {x: 60, y: 360, width: 220, height: 160};
    }
});
var plasma = new ConfigFile('plasmarc');
plasma.group = 'Theme'; plasma.writeEntry('name', 'We10XOS-dark');
