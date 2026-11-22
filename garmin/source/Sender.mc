import Toybox.Application;
import Toybox.Communications;
import Toybox.Graphics;
import Toybox.Lang;
import Toybox.WatchUi;

// Shows one line of status text; Sender updates it when the server answers.
class StatusView extends WatchUi.View {
    private var _text as String;

    function initialize(text as String) {
        View.initialize();
        _text = text;
    }

    function setText(text as String) as Void {
        _text = text;
        WatchUi.requestUpdate();
    }

    function onUpdate(dc as Graphics.Dc) as Void {
        dc.setColor(Graphics.COLOR_WHITE, Graphics.COLOR_BLACK);
        dc.clear();
        dc.drawText(dc.getWidth() / 2, dc.getHeight() / 2, Graphics.FONT_MEDIUM, _text,
                    Graphics.TEXT_JUSTIFY_CENTER | Graphics.TEXT_JUSTIFY_VCENTER);
    }
}

class Sender {
    private var _view as StatusView;

    function initialize(view as StatusView) {
        _view = view;
    }

    function send(room as String, action as String) as Void {
        var url = Application.Properties.getValue("serverUrl") as String;
        var token = Application.Properties.getValue("token") as String;
        if (token == null || token.length() == 0) {
            _view.setText("No token\nin build");
            return;
        }
        Communications.makeWebRequest(
            url,
            {"room" => room, "action" => action},
            {
                :method => Communications.HTTP_REQUEST_METHOD_POST,
                :headers => {
                    "Content-Type" => Communications.REQUEST_CONTENT_TYPE_URL_ENCODED,
                    "Authorization" => "Bearer " + token
                },
                :responseType => Communications.HTTP_RESPONSE_CONTENT_TYPE_JSON
            },
            method(:onResponse)
        );
    }

    function onResponse(code as Number, data as Dictionary or String or Null) as Void {
        if (code == 200) {
            _view.setText("Done");
        } else if (code == 403) {
            _view.setText("Bad token");
        } else if (code < 0) {
            _view.setText("No phone link\n(" + code + ")");
        } else {
            _view.setText("Failed (" + code + ")");
        }
    }
}
