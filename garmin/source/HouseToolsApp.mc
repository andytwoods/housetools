import Toybox.Application;
import Toybox.Lang;
import Toybox.WatchUi;

// Pick a room (Ryan's first), then a sound; the server plays it on that room's Echo.
class HouseToolsApp extends Application.AppBase {
    function initialize() {
        AppBase.initialize();
    }

    function getInitialView() as [WatchUi.Views] or [WatchUi.Views, WatchUi.InputDelegates] {
        return [new RoomMenu(), new RoomMenuDelegate()];
    }
}
