import Toybox.Lang;
import Toybox.WatchUi;

// Room ids match VOICE_MONKEY_DEVICES in dns/views.py.
const ROOMS = [
    ["RYAN", "Ryan"],
    ["ROBIN", "Robin"],
    ["PARENTS", "Parents"],
    ["LIVINGROOM", "Living room"],
    ["KITCHEN", "Kitchen"]
];

// Action ids match WATCH_SOUNDS in dns/views.py.
const ACTIONS = [
    ["alarm", "Alarm"],
    ["benny", "Benny Hill"],
    ["chime", "Chime"]
];

class RoomMenu extends WatchUi.Menu2 {
    function initialize() {
        Menu2.initialize({:title => "Room", :focus => 0});
        for (var i = 0; i < ROOMS.size(); i++) {
            addItem(new WatchUi.MenuItem(ROOMS[i][1], null, ROOMS[i][0], null));
        }
    }
}

class RoomMenuDelegate extends WatchUi.Menu2InputDelegate {
    function initialize() {
        Menu2InputDelegate.initialize();
    }

    function onSelect(item as WatchUi.MenuItem) as Void {
        var room = item.getId() as String;
        WatchUi.pushView(new ActionMenu(item.getLabel()), new ActionMenuDelegate(room), WatchUi.SLIDE_LEFT);
    }
}

class ActionMenu extends WatchUi.Menu2 {
    function initialize(roomLabel as String) {
        Menu2.initialize({:title => roomLabel});
        for (var i = 0; i < ACTIONS.size(); i++) {
            addItem(new WatchUi.MenuItem(ACTIONS[i][1], null, ACTIONS[i][0], null));
        }
    }
}

class ActionMenuDelegate extends WatchUi.Menu2InputDelegate {
    private var _room as String;

    function initialize(room as String) {
        Menu2InputDelegate.initialize();
        _room = room;
    }

    function onSelect(item as WatchUi.MenuItem) as Void {
        var view = new StatusView("Sending...");
        WatchUi.pushView(view, new WatchUi.BehaviorDelegate(), WatchUi.SLIDE_LEFT);
        new Sender(view).send(_room, item.getId() as String);
    }
}
