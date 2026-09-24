# -*- coding: utf-8 -*-
r"""
SFM Bring Near: Props
Version 1.0.0

Moves selected model animation sets into useful Row or Grid positions around
a fixed model or scene camera. The right-clicked model/camera establishes the
fixed point; other selected eligible models become the moved group.

License: CC0 1.0 Universal
Author: ChadChan3D
"""

import os
import re
import math
import time
import codecs
import base64
import traceback

import sfm
import sfmApp
import vs
from vs import movieobjects, datamodel
from PySide import QtGui, QtCore


OUT_PATH = r"C:\Users\Public\Documents\BNP_T154_Grid_Plane_Controls_RC.log"

UI_TITLE = "Bring Near: Props"

MAX_ANIMATION_SETS = 4096
MAX_SELECTED_DAGS = 4096
MAX_PARENT_DEPTH = 256
MAX_REFERENCES_PER_TARGET = 512
MAX_TOTAL_REFERENCES = 8192
MAX_ORDINARY_PARENT_VISITS = 8192

EPS = 1.0e-8
MAX_PROP_BOUND_DIM = 100000.0

VERIFY_POS_EPS = 0.05
VERIFY_ANG_DEG = 0.05
NOOP_POS_EPS = 0.01

DEFAULT_DISTANCE = 28
DEFAULT_SPACING = 28
BOUNDS_CLEARANCE = 16.0
INPUT_MAX = 100000

PLACEMENT_FRONT = u"In Front"
PLACEMENT_BEHIND = u"Behind"
PLACEMENT_LEFT = u"Left"
PLACEMENT_RIGHT = u"Right"

PLACEMENTS = (
    PLACEMENT_FRONT,
    PLACEMENT_BEHIND,
    PLACEMENT_LEFT,
    PLACEMENT_RIGHT,
)


LAYOUT_ROW = u"Row"
LAYOUT_GRID = u"Grid"

ROW_X = u"Front / Back (X)"
ROW_Y = u"Left / Right (Y)"
ROW_Z = u"Up / Down (Z)"

ROW_AXES = (
    ROW_X,
    ROW_Y,
    ROW_Z,
)

BRING_BUTTON_STYLE = (
    "QPushButton {"
    " background-color: #2f6fa6;"
    " color: white;"
    " border: 1px solid #4a82b2;"
    " border-radius: 2px;"
    " padding: 4px 12px;"
    " font-weight: bold;"
    "}"
    "QPushButton:hover {"
    " background-color: #377fba;"
    "}"
    "QPushButton:pressed {"
    " background-color: #275d8b;"
    "}"
    "QPushButton:disabled {"
    " background-color: #3b3b3b;"
    " color: #777777;"
    " border-color: #4a4a4a;"
    "}"
)


ARRANGE_BUTTON_STYLE = (
    "QPushButton {"
    " background-color: #4b4b4b;"
    " color: #e6e6e6;"
    " border: 1px solid #666666;"
    " border-radius: 2px;"
    " padding: 5px 18px;"
    "}"
    "QPushButton:hover {"
    " background-color: #565656;"
    "}"
    "QPushButton:checked {"
    " background-color: #5f7488;"
    " color: white;"
    " border: 2px solid #9cb9d3;"
    " font-weight: bold;"
    "}"
    "QPushButton:checked:hover {"
    " background-color: #687f95;"
    "}"
)

MSG_PARTIAL = (
    "Bring Near could not complete or verify the move.\n"
    "Press Ctrl+Z to undo it."
)

MSG_NOOP = "Nothing moved. The selected models are already in place."


class UserVisibleError(Exception):
    pass


# ===========================================================================
# Text / logging / identity
# ===========================================================================

def _u(value):
    try:
        if isinstance(value, unicode):
            return value
    except Exception:
        pass

    try:
        if isinstance(value, str):
            for encoding in ("utf-8", "mbcs", "cp1252", "latin-1"):
                try:
                    return value.decode(encoding)
                except Exception:
                    pass
            return value.decode("latin-1", "replace")
    except Exception:
        pass

    try:
        return unicode(value)
    except Exception:
        return u"<unprintable>"


def _axis_choice_from_ui_text(value):
    text = _u(value).strip()

    for choice in ROW_AXES:
        if text == choice:
            return choice

        plain = choice.rsplit(
            u" (",
            1,
        )[0]

        if text == plain:
            return choice

    return None


def _identity(obj):
    result = {
        "type": None,
        "name": None,
        "id": None,
        "handle": None,
    }

    if obj is None:
        return result

    try:
        result["type"] = _u(type(obj).__name__)
    except Exception:
        result["type"] = u"<unknown>"

    for key, method_name in (
        ("name", "GetName"),
        ("id", "GetId"),
        ("handle", "GetHandle"),
    ):
        try:
            result[key] = _u(getattr(obj, method_name)())
        except Exception:
            pass

    return result


def _required_id(obj, label):
    value = _identity(obj)["id"]

    if value is None:
        raise RuntimeError("%s identity unavailable" % label)

    return value


def _same(a, b):
    if a is None or b is None:
        return False

    ia = _identity(a)
    ib = _identity(b)

    if ia["id"] is not None and ib["id"] is not None:
        return ia["id"] == ib["id"]

    if ia["handle"] is not None and ib["handle"] is not None:
        return ia["handle"] == ib["handle"]

    try:
        return a == b
    except Exception:
        return a is b


def _natural_name_key(name):
    parts = re.split(u"([0-9]+)", _u(name).lower())
    key = []

    for part in parts:
        if not part:
            continue

        if re.match(u"^[0-9]+$", part):
            key.append((1, int(part)))
        else:
            key.append((0, part))

    return tuple(key)


def _append_log(lines):
    text = u"\r\n".join(lines) + u"\r\n"

    try:
        folder = os.path.dirname(OUT_PATH)

        if folder and not os.path.isdir(folder):
            os.makedirs(folder)
    except Exception:
        pass

    try:
        f = codecs.open(OUT_PATH, "a", "utf-8")
        try:
            f.write(text)
        finally:
            f.close()
    except Exception:
        try:
            print(text.encode("utf-8", "replace"))
        except Exception:
            pass


def _seconds_since(start):
    try:
        return max(0.0, float(time.time()) - float(start))
    except Exception:
        return 0.0


# ===========================================================================
# UI helpers
# ===========================================================================




def _bnp_widget_metadata(
    widget,
):
    if widget is None:
        return {
            "present": False,
            "py_id": None,
            "class": u"",
            "object_name": u"",
            "title": u"",
            "visible": False,
            "active": False,
            "top_level": False,
            "window_type": None,
            "window_flags": None,
        }

    try:
        class_name = _u(
            widget.metaObject().className()
        )
    except Exception:
        class_name = _u(
            type(
                widget
            ).__name__
        )

    try:
        object_name = _u(
            widget.objectName()
        )
    except Exception:
        object_name = u""

    try:
        title = _u(
            widget.windowTitle()
        )
    except Exception:
        title = u""

    try:
        visible = bool(
            widget.isVisible()
        )
    except Exception:
        visible = False

    try:
        active = bool(
            widget.isActiveWindow()
        )
    except Exception:
        active = False

    try:
        top_level = (
            widget.window() is widget
        )
    except Exception:
        top_level = False

    try:
        window_type = int(
            widget.windowType()
        )
    except Exception:
        window_type = None

    try:
        window_flags = int(
            widget.windowFlags()
        )
    except Exception:
        window_flags = None

    return {
        "present": True,
        "py_id": int(
            id(
                widget
            )
        ),
        "class": class_name,
        "object_name": object_name,
        "title": title,
        "visible": visible,
        "active": active,
        "top_level": top_level,
        "window_type": window_type,
        "window_flags": window_flags,
    }


def _bnp_widget_metadata_text(
    meta,
):
    return (
        u"present=%s py_id=%s class=%r object=%r title=%r visible=%s "
        u"active=%s top_level=%s window_type=%s window_flags=%s"
        % (
            _u(
                meta.get(
                    "present"
                )
            ),
            _u(
                meta.get(
                    "py_id"
                )
            ),
            _u(
                meta.get(
                    "class"
                )
            ),
            _u(
                meta.get(
                    "object_name"
                )
            ),
            _u(
                meta.get(
                    "title"
                )
            ),
            _u(
                meta.get(
                    "visible"
                )
            ),
            _u(
                meta.get(
                    "active"
                )
            ),
            _u(
                meta.get(
                    "top_level"
                )
            ),
            _u(
                meta.get(
                    "window_type"
                )
            ),
            _u(
                meta.get(
                    "window_flags"
                )
            ),
        )
    )


def _bnp_capture_verified_host(
    app,
):
    if app is None:
        raise UserVisibleError(
            "BNP could not access the Source Filmmaker Qt application."
        )

    try:
        modal = app.activeModalWidget()
    except Exception:
        modal = None

    try:
        popup = app.activePopupWidget()
    except Exception:
        popup = None

    if modal is not None or popup is not None:
        _bnp_log(
            "HOST_PREFLIGHT_BLOCK",
            u"reason=modal_or_popup modal=%s popup=%s"
            % (
                _bnp_widget_metadata_text(
                    _bnp_widget_metadata(
                        modal
                    )
                ),
                _bnp_widget_metadata_text(
                    _bnp_widget_metadata(
                        popup
                    )
                ),
            )
        )
        raise UserVisibleError(
            "Close open menus and dialogs, then run BNP again from Source Filmmaker."
        )

    try:
        candidate = app.activeWindow()
    except Exception:
        candidate = None

    meta = _bnp_widget_metadata(
        candidate
    )

    _bnp_log(
        "HOST_PREFLIGHT_CANDIDATE",
        _bnp_widget_metadata_text(
            meta
        )
    )

    if (
        candidate is None
        or meta[
            "class"
        ] != u"CQSFMMainWindow"
        or meta[
            "object_name"
        ] != u"SFMMainWindow"
    ):
        _bnp_log(
            "HOST_PREFLIGHT_BLOCK",
            u"reason=sfm_mainwindow_identity_not_confirmed %s"
            % _bnp_widget_metadata_text(
                meta
            )
        )
        raise UserVisibleError(
            "BNP could not confirm the Source Filmmaker main window. "
            "No model positions were changed."
        )

    _bnp_log(
        "HOST_PREFLIGHT_PASS",
        u"identity=CQSFMMainWindow/SFMMainWindow %s"
        % _bnp_widget_metadata_text(
            meta
        )
    )

    return candidate, meta



















def _adaptive_step_up_value(
    value,
):
    value = max(
        1,
        min(
            INPUT_MAX,
            int(
                value
            ),
        ),
    )

    bands = (
        (1, 10, 1),
        (10, 30, 2),
        (30, 62, 4),
        (62, 126, 8),
        (126, INPUT_MAX, 16),
    )

    for start, end, step in bands:
        if value < end:
            offset = value - start
            next_index = int(
                math.floor(
                    float(
                        offset
                    )
                    / float(
                        step
                    )
                )
            ) + 1
            candidate = start + (
                next_index * step
            )
            return min(
                end,
                INPUT_MAX,
                candidate,
            )

    return INPUT_MAX


def _adaptive_step_down_value(
    value,
):
    value = max(
        1,
        min(
            INPUT_MAX,
            int(
                value
            ),
        ),
    )

    if value <= 1:
        return 1

    bands = (
        (1, 10, 1),
        (10, 30, 2),
        (30, 62, 4),
        (62, 126, 8),
        (126, INPUT_MAX, 16),
    )

    for start, end, step in bands:
        if value <= end and value > start:
            offset = value - start
            previous_index = int(
                math.ceil(
                    float(
                        offset
                    )
                    / float(
                        step
                    )
                )
            ) - 1
            candidate = start + (
                previous_index * step
            )
            return max(
                1,
                candidate,
            )

    # Values above the highest clean landmark use the 126-anchored 16-unit band.
    start = 126
    step = 16
    offset = value - start
    previous_index = int(
        math.ceil(
            float(
                offset
            )
            / float(
                step
            )
        )
    ) - 1
    return max(
        126,
        start + (
            previous_index * step
        ),
    )




class StepValueWidget(QtGui.QWidget):
    def __init__(self, value, parent=None):
        QtGui.QWidget.__init__(self, parent)

        layout = QtGui.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self._minus = QtGui.QPushButton(u"-")
        self._minus.setFixedWidth(36)
        self._minus.setMinimumHeight(30)

        self._spin = QtGui.QSpinBox()
        self._spin.setRange(1, INPUT_MAX)
        self._spin.setSingleStep(1)
        self._spin.setValue(int(value))
        self._spin.setButtonSymbols(QtGui.QAbstractSpinBox.NoButtons)
        self._spin.setFixedWidth(58)
        self._spin.setAlignment(QtCore.Qt.AlignRight)

        self._plus = QtGui.QPushButton(u"+")
        self._plus.setFixedWidth(36)
        self._plus.setMinimumHeight(30)

        units = QtGui.QLabel("SFM units")

        layout.addWidget(self._minus)
        layout.addWidget(self._spin)
        layout.addWidget(self._plus)
        layout.addWidget(units)
        layout.addStretch(1)

        self._minus.clicked.connect(self._step_down)
        self._plus.clicked.connect(self._step_up)

    def _step_down(self):
        self._spin.setValue(
            _adaptive_step_down_value(
                self._spin.value()
            )
        )

    def _step_up(self):
        self._spin.setValue(
            _adaptive_step_up_value(
                self._spin.value()
            )
        )

    def value(self):
        return int(self._spin.value())




class ElidedModelNameLabel(QtGui.QLabel):
    def __init__(self, text=u"", parent=None):
        QtGui.QLabel.__init__(self, parent)
        self._full_text = u""
        self.setSizePolicy(
            QtGui.QSizePolicy.Ignored,
            QtGui.QSizePolicy.Preferred,
        )
        self.setMinimumWidth(0)
        self.setText(text)

    def setText(self, text):
        self._full_text = _u(text)
        self.setToolTip(self._full_text)
        self._apply_elision()

    def resizeEvent(self, event):
        QtGui.QLabel.resizeEvent(self, event)
        self._apply_elision()

    def _apply_elision(self):
        metrics = QtGui.QFontMetrics(self.font())
        width = max(0, self.contentsRect().width())
        QtGui.QLabel.setText(
            self,
            metrics.elidedText(
                self._full_text,
                QtCore.Qt.ElideRight,
                width,
            ),
        )


# ===========================================================================
# Finite vector / quaternion math
# ===========================================================================

def _finite_number(value):
    try:
        f = float(value)
    except Exception:
        return False

    try:
        return not math.isnan(f) and not math.isinf(f)
    except Exception:
        return False


def _require_finite_tuple(values, label):
    result = tuple(float(value) for value in values)

    if not all(_finite_number(value) for value in result):
        raise RuntimeError("%s contains non-finite values" % label)

    return result


def _vec3(value):
    return _require_finite_tuple(
        (value.x, value.y, value.z),
        "vector"
    )


def _quat4(value):
    return _require_finite_tuple(
        (value.x, value.y, value.z, value.w),
        "quaternion"
    )


def _add(a, b):
    return (
        a[0] + b[0],
        a[1] + b[1],
        a[2] + b[2],
    )


def _sub(a, b):
    return (
        a[0] - b[0],
        a[1] - b[1],
        a[2] - b[2],
    )


def _mul(value, scalar):
    return (
        value[0] * scalar,
        value[1] * scalar,
        value[2] * scalar,
    )


def _dot(a, b):
    return (
        a[0] * b[0]
        + a[1] * b[1]
        + a[2] * b[2]
    )


def _norm(value):
    value = _require_finite_tuple(value, "vector")
    n2 = _dot(value, value)

    if not _finite_number(n2) or n2 < 0.0:
        raise RuntimeError("invalid vector norm")

    result = math.sqrt(n2)

    if not _finite_number(result):
        raise RuntimeError("invalid vector norm")

    return result


def _normalize(value):
    n = _norm(value)

    if n <= EPS:
        raise RuntimeError("degenerate vector")

    return _mul(value, 1.0 / n)


def _distance(a, b):
    return _norm(_sub(a, b))


def _qnorm(q):
    return math.sqrt(
        q[0] * q[0]
        + q[1] * q[1]
        + q[2] * q[2]
        + q[3] * q[3]
    )


def _qangle_deg(a, b):
    a = _require_finite_tuple(a, "quaternion A")
    b = _require_finite_tuple(b, "quaternion B")

    na = _qnorm(a)
    nb = _qnorm(b)

    if (
        not _finite_number(na)
        or not _finite_number(nb)
        or na <= EPS
        or nb <= EPS
    ):
        raise RuntimeError("invalid quaternion norm")

    d = abs(
        (
            a[0] * b[0]
            + a[1] * b[1]
            + a[2] * b[2]
            + a[3] * b[3]
        )
        / (na * nb)
    )

    d = max(0.0, min(1.0, d))
    result = math.degrees(2.0 * math.acos(d))

    if not _finite_number(result):
        raise RuntimeError("invalid quaternion angle")

    return result


def _display_axes_from_quaternion(q):
    """
    Artist-facing axes qualified by T07/T08.

    Source AngleVectors returns:
        forward = local +X
        right   = local -Y
        up      = local +Z

    The returned Source "right" was visually qualified as Props Right.
    """
    qa = vs.QAngle()
    vs.mathlib.QuaternionAngles(q, qa)

    forward = vs.Vector(0, 0, 0)
    right = vs.Vector(0, 0, 0)
    up = vs.Vector(0, 0, 0)

    vs.mathlib.AngleVectors(
        qa,
        forward,
        right,
        up,
    )

    return (
        _normalize(_vec3(forward)),
        _normalize(_vec3(right)),
        _normalize(_vec3(up)),
    )


def _local_axes_from_quaternion(q):
    """
    Local basis for StudioHdr coordinates.

    Local +Y is the negative of Source AngleVectors' artist-facing right.
    """
    forward, right, up = _display_axes_from_quaternion(q)

    return (
        forward,
        _mul(right, -1.0),
        up,
    )


def _rotate_xyz_for_quaternion(q):
    qa = vs.QAngle()
    vs.mathlib.QuaternionAngles(q, qa)

    # Qualified Bring Near: Lights mapping:
    # sfm.Rotate(X, Y, Z) == (roll, pitch, yaw).
    return (
        float(qa.z),
        float(qa.x),
        float(qa.y),
    )


# ===========================================================================
# Timeline / current-shot context
# ===========================================================================

def _timeline_snapshot():
    try:
        if not sfmApp.HasDocument():
            raise RuntimeError("no open document")
    except Exception:
        raise RuntimeError("document state unavailable")

    try:
        document = sfmApp.GetDocumentRoot()
    except Exception:
        raise RuntimeError("document root unavailable")

    if document is None:
        raise RuntimeError("document root unavailable")

    try:
        mode = sfmApp.GetTimelineMode()
        mode_name = _u(sfmApp.GetNameForTimelineMode(mode))
        head_frames = float(sfmApp.GetHeadTimeInFrames())
        head_seconds = float(sfmApp.GetHeadTimeInSeconds())
        live_shot = sfmApp.GetShotAtCurrentTime()
    except Exception:
        raise RuntimeError("timeline context unavailable")

    if not _finite_number(head_frames) or not _finite_number(head_seconds):
        raise RuntimeError("timeline head invalid")

    return {
        "document_id": _required_id(document, "document root"),
        "mode": mode,
        "mode_name": mode_name,
        "head_frames": head_frames,
        "head_seconds": head_seconds,
        "live_shot_id": (
            _required_id(live_shot, "live shot")
            if live_shot is not None
            else None
        ),
    }




# ===========================================================================
# Animation-set / owner reconstruction
# ===========================================================================

def _shot_animation_sets(shot):
    try:
        arr = shot.animationSets
        count = len(arr)
    except Exception:
        raise RuntimeError("shot animation sets unreadable")

    if count < 0 or count > MAX_ANIMATION_SETS:
        raise RuntimeError("shot animation-set limit")

    return [arr[index] for index in range(count)]


def _element_record(aset, kind, element):
    return {
        "kind": kind,
        "aset": aset,
        "aset_info": _identity(aset),
        "element": element,
        "element_info": _identity(element),
    }


def _build_owner_maps(shot):
    by_element_id = {}
    by_aset_id = {}
    all_records = []

    for aset in _shot_animation_sets(shot):
        aset_info = _identity(aset)

        if aset_info["id"] is None:
            continue

        record = None

        try:
            gm = aset.gameModel
        except Exception:
            gm = None

        if gm is not None and _identity(gm)["id"] is not None:
            record = _element_record(
                aset,
                "MODEL",
                gm,
            )

        if record is None:
            try:
                camera = aset.camera
            except Exception:
                camera = None

            if camera is not None and _identity(camera)["id"] is not None:
                record = _element_record(
                    aset,
                    "CAMERA",
                    camera,
                )

        if record is None:
            try:
                light = aset.light
            except Exception:
                light = None

            if light is not None:
                try:
                    light_dag = movieobjects.CastElementAsDmeDag(light)
                except Exception:
                    light_dag = None

                if light_dag is not None and _identity(light_dag)["id"] is not None:
                    record = _element_record(
                        aset,
                        "LIGHT",
                        light_dag,
                    )

        if record is None:
            continue

        element_id = record["element_info"]["id"]
        aset_id = record["aset_info"]["id"]

        by_element_id[element_id] = record
        by_aset_id[aset_id] = record
        all_records.append(record)

    return by_element_id, by_aset_id, all_records


def _resolve_owner_from_parent_chain(dag, owner_by_element_id):
    current = dag
    seen = set()

    for depth in range(MAX_PARENT_DEPTH + 1):
        info = _identity(current)
        current_id = info["id"]

        if current_id is not None and current_id in owner_by_element_id:
            return owner_by_element_id[current_id]

        key = (
            current_id
            or info["handle"]
            or (u"%s:%s" % (info["type"], info["name"]))
        )

        if key in seen:
            return None

        seen.add(key)

        try:
            parent = current.GetParent()
        except Exception:
            return None

        if parent is None:
            return None

        current = parent

    return None


def _selected_owner_snapshot(owner_by_element_id):
    owner_ids = set()
    unresolved = 0
    selected_dag_count = 0
    seen = set()

    dag = sfm.FirstSelectedDag()

    while dag is not None:
        if selected_dag_count >= MAX_SELECTED_DAGS:
            raise RuntimeError("selected DAG limit")

        info = _identity(dag)
        key = (
            info["id"]
            or info["handle"]
            or (u"%s:%s" % (info["type"], info["name"]))
        )

        if key in seen:
            raise RuntimeError("selected DAG iterator cycle")

        seen.add(key)
        selected_dag_count += 1

        owner = _resolve_owner_from_parent_chain(
            dag,
            owner_by_element_id,
        )

        if owner is None:
            unresolved += 1
        else:
            owner_ids.add(owner["aset_info"]["id"])

        dag = sfm.NextSelectedDag()

    return {
        "owner_ids": owner_ids,
        "unresolved": unresolved,
        "selected_dag_count": selected_dag_count,
    }


# ===========================================================================
# Model transform resolution / parent state
# ===========================================================================

def _resolve_model_record(record):
    if record is None or record["kind"] != "MODEL":
        raise RuntimeError("target is not a model")

    aset = record["aset"]
    gm = record["element"]

    try:
        ctrl = aset.FindTransformControl(gm)
    except Exception:
        ctrl = None

    if ctrl is None:
        raise RuntimeError(
            "model transform control unavailable: %s"
            % _u(record["aset_info"]["name"])
        )

    try:
        ctrl_dag = ctrl.GetDag()
    except Exception:
        ctrl_dag = None

    if ctrl_dag is None or not _same(ctrl_dag, gm):
        raise RuntimeError(
            "model transform control DAG mismatch: %s"
            % _u(record["aset_info"]["name"])
        )

    try:
        transform = ctrl.GetTransform()
    except Exception:
        transform = None

    if transform is None:
        raise RuntimeError(
            "model transform unavailable: %s"
            % _u(record["aset_info"]["name"])
        )

    try:
        transform_dag = transform.GetDag()
    except Exception:
        transform_dag = None

    if transform_dag is None or not _same(transform_dag, gm):
        raise RuntimeError(
            "model transform DAG mismatch: %s"
            % _u(record["aset_info"]["name"])
        )

    return {
        "record": record,
        "aset": aset,
        "gm": gm,
        "ctrl": ctrl,
        "transform": transform,
        "aset_id": _required_id(aset, "model animation set"),
        "gm_id": _required_id(gm, "model gameModel"),
        "ctrl_id": _required_id(ctrl, "model transform control"),
        "transform_id": _required_id(transform, "model transform"),
    }


def _optional_parent_state(dag):
    try:
        parent = dag.GetParent()
    except Exception:
        return {
            "complete": False,
            "present": None,
            "id": None,
        }

    if parent is None:
        return {
            "complete": True,
            "present": False,
            "id": None,
        }

    parent_id = _identity(parent)["id"]

    if parent_id is None:
        return {
            "complete": False,
            "present": True,
            "id": None,
        }

    return {
        "complete": True,
        "present": True,
        "id": parent_id,
    }


def _same_optional_parent(a, b):
    if not a["complete"] or not b["complete"]:
        return False

    if a["present"] != b["present"]:
        return False

    if not a["present"]:
        return True

    return a["id"] == b["id"]


# ===========================================================================
# Relationship classification
# ===========================================================================

def _reverse_override_state(dag, total_budget):
    result = {
        "complete": False,
        "outbound": False,
        "owner": None,
        "visited": 0,
        "error": None,
    }

    try:
        dm = datamodel.g_pDataModel
        token = dm.FirstAttributeReferencingElement(dag.GetHandle())
    except Exception:
        result["error"] = u"reference scan could not start"
        return result

    seen = set()

    try:
        while token != 0:
            if token in seen:
                raise RuntimeError("reference iterator cycle")

            if len(seen) >= MAX_REFERENCES_PER_TARGET:
                raise RuntimeError("per-target reference limit")

            if total_budget[0] >= MAX_TOTAL_REFERENCES:
                raise RuntimeError("total reference limit")

            seen.add(token)
            result["visited"] += 1
            total_budget[0] += 1

            attr = dm.GetAttributeFromIterator(token)

            if attr is None:
                raise RuntimeError("reference attribute unreadable")

            if _u(attr.GetName()) == u"overrideParent":
                owner = attr.GetOwner()

                if owner is None:
                    raise RuntimeError("overrideParent owner unreadable")

                result["complete"] = True
                result["outbound"] = True
                result["owner"] = owner
                return result

            token = dm.NextAttributeReferencingElement(token)

        result["complete"] = True

    except Exception:
        result["error"] = _u(traceback.format_exc())

    return result


def _ordinary_inbound_owner(
    root,
    owner_by_element_id,
    ordinary_budget
):
    current = root
    seen = set()
    own_id = _identity(root)["id"]

    for depth in range(MAX_PARENT_DEPTH + 1):
        ordinary_budget[0] += 1

        if ordinary_budget[0] > MAX_ORDINARY_PARENT_VISITS:
            return {
                "complete": False,
                "owner": None,
                "error": u"ordinary parent budget exceeded",
            }

        try:
            parent = current.GetParent()
        except Exception:
            return {
                "complete": False,
                "owner": None,
                "error": u"ordinary parent unreadable",
            }

        if parent is None:
            return {
                "complete": True,
                "owner": None,
                "error": None,
            }

        info = _identity(parent)
        key = (
            info["id"]
            or info["handle"]
            or (u"%s:%s" % (info["type"], info["name"]))
        )

        if key in seen:
            return {
                "complete": False,
                "owner": None,
                "error": u"ordinary parent cycle",
            }

        seen.add(key)

        if (
            info["id"] is not None
            and info["id"] != own_id
            and info["id"] in owner_by_element_id
        ):
            return {
                "complete": True,
                "owner": owner_by_element_id[info["id"]],
                "error": None,
            }

        current = parent

    return {
        "complete": False,
        "owner": None,
        "error": u"ordinary parent depth limit",
    }


def _ordinary_outbound_owner(
    target,
    all_owner_records,
    ordinary_budget
):
    target_id = target["element_info"]["id"]

    for other in all_owner_records:
        if other["aset_info"]["id"] == target["aset_info"]["id"]:
            continue

        current = other["element"]
        seen = set()

        for depth in range(MAX_PARENT_DEPTH + 1):
            ordinary_budget[0] += 1

            if ordinary_budget[0] > MAX_ORDINARY_PARENT_VISITS:
                return {
                    "complete": False,
                    "owner": None,
                    "error": u"ordinary peer budget exceeded",
                }

            try:
                parent = current.GetParent()
            except Exception:
                return {
                    "complete": False,
                    "owner": None,
                    "error": u"ordinary peer parent unreadable",
                }

            if parent is None:
                break

            info = _identity(parent)
            key = (
                info["id"]
                or info["handle"]
                or (u"%s:%s" % (info["type"], info["name"]))
            )

            if key in seen:
                return {
                    "complete": False,
                    "owner": None,
                    "error": u"ordinary peer parent cycle",
                }

            seen.add(key)

            if info["id"] == target_id:
                return {
                    "complete": True,
                    "owner": other,
                    "error": None,
                }

            current = parent

    return {
        "complete": True,
        "owner": None,
        "error": None,
    }


def _target_relationship_state(
    target_record,
    owner_by_element_id,
    all_owner_records,
    reference_budget,
    ordinary_budget
):
    gm = target_record["element"]

    try:
        stored_parent = gm.GetOverrideParent(True)
    except Exception:
        return {
            "state": "UNKNOWN",
            "reason": u"Relationships could not be verified.",
            "owner": None,
            "reference_visits": 0,
        }

    if stored_parent is not None:
        return {
            "state": "BLOCKED_INBOUND",
            "reason": u"Locked to another object.",
            "owner": stored_parent,
            "reference_visits": 0,
        }

    reverse = _reverse_override_state(
        gm,
        reference_budget,
    )

    if reverse["outbound"]:
        return {
            "state": "BLOCKED_OUTBOUND",
            "reason": u"Another object is locked to this model.",
            "owner": reverse["owner"],
            "reference_visits": reverse["visited"],
        }

    if not reverse["complete"]:
        return {
            "state": "UNKNOWN",
            "reason": u"Relationships could not be verified.",
            "owner": None,
            "reference_visits": reverse["visited"],
        }

    ordinary_in = _ordinary_inbound_owner(
        gm,
        owner_by_element_id,
        ordinary_budget,
    )

    if not ordinary_in["complete"]:
        return {
            "state": "UNKNOWN",
            "reason": u"Parent relationships could not be verified.",
            "owner": None,
            "reference_visits": reverse["visited"],
        }

    if ordinary_in["owner"] is not None:
        return {
            "state": "BLOCKED_ORDINARY_IN",
            "reason": u"Parented to another object.",
            "owner": ordinary_in["owner"]["element"],
            "reference_visits": reverse["visited"],
        }

    ordinary_out = _ordinary_outbound_owner(
        target_record,
        all_owner_records,
        ordinary_budget,
    )

    if not ordinary_out["complete"]:
        return {
            "state": "UNKNOWN",
            "reason": u"Parent relationships could not be verified.",
            "owner": None,
            "reference_visits": reverse["visited"],
        }

    if ordinary_out["owner"] is not None:
        return {
            "state": "BLOCKED_ORDINARY_OUT",
            "reason": u"Another object is parented to this model.",
            "owner": ordinary_out["owner"]["element"],
            "reference_visits": reverse["visited"],
        }

    return {
        "state": "FREE",
        "reason": None,
        "owner": None,
        "reference_visits": reverse["visited"],
    }


# ===========================================================================
# Bounds / projected extents
# ===========================================================================

def _header_vector(hdr, name):
    value = getattr(hdr, name)

    try:
        if callable(value):
            value = value()
    except Exception:
        pass

    return _vec3(value)


def _bounds_pair_valid(mins, maxs):
    mins = _require_finite_tuple(mins, "bounds mins")
    maxs = _require_finite_tuple(maxs, "bounds maxs")

    dims = (
        maxs[0] - mins[0],
        maxs[1] - mins[1],
        maxs[2] - mins[2],
    )

    if any(dim < -EPS for dim in dims):
        return False, None

    dims = tuple(max(0.0, dim) for dim in dims)

    if max(dims) <= EPS or max(dims) > MAX_PROP_BOUND_DIM:
        return False, dims

    return True, dims


def _local_point_to_world(dag, point):
    origin = _vec3(dag.GetAbsPosition())
    local_x, local_y, local_z = _local_axes_from_quaternion(
        dag.GetAbsOrientation()
    )

    world = origin
    world = _add(world, _mul(local_x, point[0]))
    world = _add(world, _mul(local_y, point[1]))
    world = _add(world, _mul(local_z, point[2]))

    return world


def _bounds_info(gm):
    result = {
        "usable": False,
        "source": "root",
        "mins": None,
        "maxs": None,
        "dims": None,
        "center": _vec3(gm.GetAbsPosition()),
    }

    try:
        hdr = gm.GetStudioHdr()
    except Exception:
        return result

    if hdr is None:
        return result

    view_min = None
    view_max = None
    hull_min = None
    hull_max = None

    try:
        view_min = _header_vector(hdr, "view_bbmin")
        view_max = _header_vector(hdr, "view_bbmax")
    except Exception:
        pass

    try:
        hull_min = _header_vector(hdr, "hull_min")
        hull_max = _header_vector(hdr, "hull_max")
    except Exception:
        pass

    chosen_min = None
    chosen_max = None
    chosen_dims = None
    source = None

    if view_min is not None and view_max is not None:
        nonzero = any(
            abs(value) > EPS
            for value in (view_min + view_max)
        )
        valid, dims = _bounds_pair_valid(
            view_min,
            view_max,
        )

        if nonzero and valid:
            chosen_min = view_min
            chosen_max = view_max
            chosen_dims = dims
            source = "view_bb"

    if (
        chosen_dims is None
        and hull_min is not None
        and hull_max is not None
    ):
        valid, dims = _bounds_pair_valid(
            hull_min,
            hull_max,
        )

        if valid:
            chosen_min = hull_min
            chosen_max = hull_max
            chosen_dims = dims
            source = "hull"

    if chosen_dims is None:
        return result

    local_center = (
        (chosen_min[0] + chosen_max[0]) * 0.5,
        (chosen_min[1] + chosen_max[1]) * 0.5,
        (chosen_min[2] + chosen_max[2]) * 0.5,
    )

    result["usable"] = True
    result["source"] = source
    result["mins"] = chosen_min
    result["maxs"] = chosen_max
    result["dims"] = chosen_dims
    result["center"] = _local_point_to_world(
        gm,
        local_center,
    )

    return result




# ===========================================================================
# Preflight / live snapshot
# ===========================================================================

def _reference_dag(record):
    if record["kind"] == "MODEL":
        return record["element"]

    if record["kind"] == "CAMERA":
        dag = movieobjects.CastElementAsDmeDag(record["element"])

        if dag is None:
            raise RuntimeError("scene camera DAG unavailable")

        return dag

    raise RuntimeError("unsupported reference type")




def _blocked_message(blocked):
    lines = [
        u"Nothing moved. Fix these model relationships, then run Bring Near again:",
        u"",
    ]

    for item in blocked:
        lines.append(
            u"%s - %s"
            % (
                _u(item["record"]["aset_info"]["name"]),
                _u(item["relationship"]["reason"]),
            )
        )

    return u"\n".join(lines)




# ===========================================================================
# Pure placement planner
# ===========================================================================

def _placement_direction(reference_axes, placement):
    forward, right, up = reference_axes

    if placement == PLACEMENT_FRONT:
        return forward

    if placement == PLACEMENT_BEHIND:
        return _mul(forward, -1.0)

    if placement == PLACEMENT_LEFT:
        return _mul(right, -1.0)

    if placement == PLACEMENT_RIGHT:
        return right

    raise RuntimeError("unknown placement")


def _axis_vector(reference_axes, direction_choice):
    forward, right, up = reference_axes

    if direction_choice == ROW_X:
        return forward

    if direction_choice == ROW_Y:
        return right

    if direction_choice == ROW_Z:
        return up

    raise RuntimeError("unknown arrangement direction")


def _axis_positions(
    count,
    spacing,
):
    count = int(
        count
    )

    if count <= 0:
        return []

    spacing = float(
        spacing
    )
    center_index = (
        float(
            count - 1
        )
        * 0.5
    )

    return [
        (
            float(
                index
            )
            - center_index
        )
        * spacing
        for index in range(
            count
        )
    ]




def _layout_offsets(
    rows,
    reference_axes,
    layout_mode,
    direction1,
    direction2,
    minimum_spacing
):
    axis_a = _axis_vector(
        reference_axes,
        direction1,
    )

    if layout_mode == LAYOUT_ROW:
        positions = _axis_positions(
            len(
                rows
            ),
            minimum_spacing,
        )

        for row in rows:
            row["layout_extent_a"] = 0.0
            row["layout_extent_b"] = 0.0

        offsets = [
            _mul(
                axis_a,
                positions[
                    index
                ],
            )
            for index in range(
                len(
                    rows
                )
            )
        ]

        return {
            "mode": LAYOUT_ROW,
            "direction1": direction1,
            "direction2": None,
            "axis_a": axis_a,
            "axis_b": None,
            "columns": len(
                rows
            ),
            "rows": 1,
            "offsets": offsets,
        }

    if layout_mode != LAYOUT_GRID:
        raise RuntimeError(
            "unknown layout mode"
        )

    if (
        direction2 is None
        or direction2 == direction1
    ):
        raise RuntimeError(
            "grid directions must be different"
        )

    axis_b = _axis_vector(
        reference_axes,
        direction2,
    )

    count = len(
        rows
    )
    columns = int(
        math.ceil(
            math.sqrt(
                float(
                    count
                )
            )
        )
    )
    grid_rows = int(
        math.ceil(
            float(
                count
            )
            / float(
                columns
            )
        )
    )

    column_positions = _axis_positions(
        columns,
        minimum_spacing,
    )
    row_positions = _axis_positions(
        grid_rows,
        minimum_spacing,
    )

    for row in rows:
        row["layout_extent_a"] = 0.0
        row["layout_extent_b"] = 0.0

    offsets = []

    for index, row in enumerate(
        rows
    ):
        column = index % columns
        grid_row = index // columns

        offset = _add(
            _mul(
                axis_a,
                column_positions[
                    column
                ],
            ),
            _mul(
                axis_b,
                row_positions[
                    grid_row
                ],
            ),
        )
        offsets.append(
            offset
        )

    return {
        "mode": LAYOUT_GRID,
        "direction1": direction1,
        "direction2": direction2,
        "axis_a": axis_a,
        "axis_b": axis_b,
        "columns": columns,
        "rows": grid_rows,
        "offsets": offsets,
    }


def _build_plans(
    live_state,
    placement,
    layout_mode,
    direction1,
    direction2,
    minimum_distance,
    minimum_spacing
):
    direction = _placement_direction(
        live_state[
            "reference_axes"
        ],
        placement,
    )

    reference_origin = live_state[
        "reference_pos"
    ]

    rows = []

    for geometry in live_state[
        "target_geometry"
    ]:
        resolved = geometry[
            "resolved"
        ]

        rows.append({
            "geometry": geometry,
            "name": resolved[
                "record"
            ][
                "aset_info"
            ][
                "name"
            ],
            "gm": resolved[
                "gm"
            ],
            "bounds": geometry[
                "bounds"
            ],
            "visual_center": geometry[
                "root_pos"
            ],
            "direction_extent": 0.0,
            "layout_extent_a": 0.0,
            "layout_extent_b": 0.0,
        })

    layout = _layout_offsets(
        rows,
        live_state[
            "reference_axes"
        ],
        layout_mode,
        direction1,
        direction2,
        minimum_spacing,
    )

    # Preserve the existing side rule without using bounds: when the selected
    # spread axis itself points through the reference, shift only enough that
    # all target origins remain on the chosen side.
    needed_distances = []

    for index, row in enumerate(
        rows
    ):
        offset_along_direction = _dot(
            layout[
                "offsets"
            ][
                index
            ],
            direction,
        )
        needed_distances.append(
            -offset_along_direction
        )

    actual_distance = max(
        [
            float(
                minimum_distance
            )
        ]
        + needed_distances
    )

    layout_origin = _add(
        reference_origin,
        _mul(
            direction,
            actual_distance,
        ),
    )

    plans = []

    for index, row in enumerate(
        rows
    ):
        layout_offset = layout[
            "offsets"
        ][
            index
        ]

        desired_center = _add(
            layout_origin,
            layout_offset,
        )

        before_root = row[
            "geometry"
        ][
            "root_pos"
        ]

        destination_root = _require_finite_tuple(
            desired_center,
            "planned destination",
        )

        before_q = row[
            "geometry"
        ][
            "root_q"
        ]
        rotate_xyz = _require_finite_tuple(
            _rotate_xyz_for_quaternion(
                row[
                    "gm"
                ].GetAbsOrientation()
            ),
            "planned unchanged rotation",
        )

        pos_delta = _distance(
            before_root,
            destination_root,
        )

        plans.append({
            "index": index,
            "name": row[
                "name"
            ],
            "resolved": row[
                "geometry"
            ][
                "resolved"
            ],
            "gm": row[
                "gm"
            ],
            "bounds": row[
                "bounds"
            ],
            "direction_extent": 0.0,
            "layout_extent_a": 0.0,
            "layout_extent_b": 0.0,
            "layout_offset": layout_offset,
            "desired_center": desired_center,
            "destination_root": destination_root,
            "before_root": before_root,
            "before_q": before_q,
            "before_parent_state": row[
                "geometry"
            ][
                "parent_state"
            ],
            "rotate_xyz": rotate_xyz,
            "noop": pos_delta <= NOOP_POS_EPS,
            "pre_position_delta": pos_delta,
        })

    return {
        "placement": placement,
        "layout_mode": layout_mode,
        "direction1": direction1,
        "direction2": direction2,
        "direction": direction,
        "layout_axis_a": layout[
            "axis_a"
        ],
        "layout_axis_b": layout[
            "axis_b"
        ],
        "grid_columns": layout[
            "columns"
        ],
        "grid_rows": layout[
            "rows"
        ],
        "reference_origin": reference_origin,
        "reference_direction_extent": 0.0,
        "minimum_distance": float(
            minimum_distance
        ),
        "actual_distance": actual_distance,
        "minimum_spacing": float(
            minimum_spacing
        ),
        "layout_origin": layout_origin,
        "plans": plans,
    }



# ===========================================================================
# T31 hardening / captured-session helpers
# ===========================================================================

APP_ATTR = "_chadchan3d_bnp_t32_modeless_window"

TEST_UNDO_NAME = "Bring Near Props"
TEST_REDO_NAME = "Redo Bring Near Props"

TEST_PLACEMENT = PLACEMENT_FRONT
TEST_LAYOUT = LAYOUT_ROW
TEST_DIRECTION1 = ROW_Y
TEST_DIRECTION2 = None
TEST_DISTANCE = DEFAULT_DISTANCE
TEST_SPACING = DEFAULT_SPACING


def _ordinary_outbound_owner(
    target,
    all_owner_records,
    ordinary_budget
):
    """
    T31 fail-closed correction over the T20 helper:
    exhausting MAX_PARENT_DEPTH for any peer is UNKNOWN, never FREE.
    """
    target_id = target["element_info"]["id"]

    for other in all_owner_records:
        if other["aset_info"]["id"] == target["aset_info"]["id"]:
            continue

        current = other["element"]
        seen = set()
        reached_root = False

        for depth in range(MAX_PARENT_DEPTH + 1):
            ordinary_budget[0] += 1

            if ordinary_budget[0] > MAX_ORDINARY_PARENT_VISITS:
                return {
                    "complete": False,
                    "owner": None,
                    "error": u"ordinary peer budget exceeded",
                }

            try:
                parent = current.GetParent()
            except Exception:
                return {
                    "complete": False,
                    "owner": None,
                    "error": u"ordinary peer parent unreadable",
                }

            if parent is None:
                reached_root = True
                break

            info = _identity(parent)
            key = (
                info["id"]
                or info["handle"]
                or (u"%s:%s" % (info["type"], info["name"]))
            )

            if key in seen:
                return {
                    "complete": False,
                    "owner": None,
                    "error": u"ordinary peer parent cycle",
                }

            seen.add(key)

            if info["id"] == target_id:
                return {
                    "complete": True,
                    "owner": other,
                    "error": None,
                }

            current = parent

        if not reached_root:
            return {
                "complete": False,
                "owner": None,
                "error": u"ordinary peer parent depth limit",
            }

    return {
        "complete": True,
        "owner": None,
        "error": None,
    }


def _unsupported_selection_message(records):
    cameras = [
        record
        for record in records
        if record["kind"] == "CAMERA"
    ]
    lights = [
        record
        for record in records
        if record["kind"] == "LIGHT"
    ]
    others = [
        record
        for record in records
        if record["kind"] not in (
            "CAMERA",
            "LIGHT",
        )
    ]

    if cameras and not lights and not others:
        if len(cameras) == 1:
            name = _u(
                cameras[
                    0
                ][
                    "aset_info"
                ][
                    "name"
                ]
            )
            return (
                u"%s is a camera. Bring Near: Props cannot move cameras."
                % name
            )

        return (
            u"Bring Near: Props cannot move cameras."
        )

    if lights and not cameras and not others:
        return (
            u"Bring Near: Props cannot move lights. "
            u"If you have Bring Near: Lights, use it to position them."
        )

    if cameras and lights:
        return (
            u"Bring Near: Props cannot move cameras or lights."
        )

    if cameras:
        return (
            u"Bring Near: Props cannot move cameras."
        )

    if lights:
        return (
            u"Bring Near: Props cannot move lights. "
            u"If you have Bring Near: Lights, use it to position them."
        )

    return (
        u"Bring Near: Props moves models. Select models to add."
    )


def _capture_initial_session():
    timeline = _timeline_snapshot()

    shot = sfm.GetCurrentShot()
    reference_aset = sfm.GetCurrentAnimationSet()

    if shot is None or reference_aset is None:
        raise UserVisibleError(
            "Right-click a model or scene camera, then run Bring Near again."
        )

    shot_id = _required_id(shot, "current shot")
    reference_id = _required_id(
        reference_aset,
        "invoking Animation Set",
    )

    if timeline["live_shot_id"] != shot_id:
        raise RuntimeError(
            "current Rig shot does not match playhead shot"
        )

    owner_by_element_id, by_aset_id, _ = _build_owner_maps(
        shot
    )

    reference = by_aset_id.get(reference_id)

    if reference is None:
        raise RuntimeError(
            "reference owner could not be reconstructed"
        )

    if reference["kind"] not in ("MODEL", "CAMERA"):
        raise UserVisibleError(
            "Right-click a model or scene camera, then run Bring Near again."
        )

    selection = _selected_owner_snapshot(
        owner_by_element_id
    )

    if selection["unresolved"] != 0:
        _bnp_log(
            "SELECTION_UNRESOLVED_IGNORED",
            u"phase=initial unresolved=%d selected_dags=%d resolved_owners=%d reference=%s"
            % (
                selection["unresolved"],
                selection["selected_dag_count"],
                len(
                    selection["owner_ids"]
                ),
                _u(
                    reference["aset_info"]["name"]
                ),
            )
        )

    targets = []
    unsupported = []

    for aset_id in selection["owner_ids"]:
        if aset_id == reference_id:
            continue

        record = by_aset_id.get(aset_id)

        if record is None:
            raise RuntimeError(
                "selected owner could not be re-resolved"
            )

        if record["kind"] == "MODEL":
            targets.append(record)
        else:
            unsupported.append(record)

    targets.sort(
        key=lambda record: (
            _natural_name_key(
                record["aset_info"]["name"]
            ),
            _u(record["aset_info"]["id"]),
        )
    )

    unsupported.sort(
        key=lambda record: (
            _natural_name_key(
                record["aset_info"]["name"]
            ),
            _u(record["aset_info"]["id"]),
        )
    )

    if unsupported:
        raise UserVisibleError(
            _unsupported_selection_message(
                unsupported
            )
        )

    return {
        "document_id": timeline["document_id"],
        "shot_id": shot_id,
        "shot_name": _u(_identity(shot)["name"]),
        "reference_id": reference_id,
        "reference_name": _u(
            reference["aset_info"]["name"]
        ),
        "reference_kind": reference["kind"],
        "target_ids": [
            record["aset_info"]["id"]
            for record in targets
        ],
        "target_names": [
            _u(record["aset_info"]["name"])
            for record in targets
        ],
        "selected_dags": selection[
            "selected_dag_count"
        ],
    }


def _capture_merge_from_fresh_rig(window):
    timeline = _timeline_snapshot()

    if timeline["document_id"] != window.document_id():
        raise UserVisibleError(
            "This Bring Near session belongs to another document. Close it and start again."
        )

    if timeline["live_shot_id"] != window.shot_id():
        raise UserVisibleError(
            "Return to the shot where this Bring Near session started."
        )

    shot = sfm.GetCurrentShot()
    invoking = sfm.GetCurrentAnimationSet()

    if shot is None or invoking is None:
        raise RuntimeError(
            "fresh Rig shot/invoking Animation Set unavailable"
        )

    if _required_id(shot, "fresh Rig shot") != window.shot_id():
        raise UserVisibleError(
            "Return to the shot where this Bring Near session started."
        )

    owner_by_element_id, by_aset_id, _ = _build_owner_maps(
        shot
    )

    reference = by_aset_id.get(
        window.reference_id()
    )

    if reference is None:
        raise UserVisibleError(
            "The Place near model or camera is no longer available."
        )

    selection = _selected_owner_snapshot(
        owner_by_element_id
    )

    if selection["unresolved"] != 0:
        _bnp_log(
            "SELECTION_UNRESOLVED_IGNORED",
            u"phase=merge unresolved=%d selected_dags=%d resolved_owners=%d reference=%s"
            % (
                selection["unresolved"],
                selection["selected_dag_count"],
                len(
                    selection["owner_ids"]
                ),
                _u(
                    reference["aset_info"]["name"]
                ),
            )
        )

    models = []
    unsupported = []

    for aset_id in selection["owner_ids"]:
        if aset_id == window.reference_id():
            continue

        record = by_aset_id.get(aset_id)

        if record is None:
            raise RuntimeError(
                "selected owner could not be re-resolved"
            )

        if record["kind"] == "MODEL":
            models.append(record)
        else:
            unsupported.append(record)

    if unsupported:
        unsupported.sort(
            key=lambda record: (
                _natural_name_key(
                    record["aset_info"]["name"]
                ),
                _u(record["aset_info"]["id"]),
            )
        )
        raise UserVisibleError(
            _unsupported_selection_message(
                unsupported
            )
        )

    models.sort(
        key=lambda record: (
            _natural_name_key(
                record["aset_info"]["name"]
            ),
            _u(record["aset_info"]["id"]),
        )
    )

    return {
        "invoking_name": _u(
            _identity(invoking)["name"]
        ),
        "models": [
            {
                "id": record["aset_info"]["id"],
                "name": _u(
                    record["aset_info"]["name"]
                ),
            }
            for record in models
        ],
        "selected_dags": selection[
            "selected_dag_count"
        ],
        "owner_count": len(
            selection["owner_ids"]
        ),
    }


def _live_session_shot(
    document_id,
    shot_id,
):
    timeline = _timeline_snapshot()

    if timeline["document_id"] != document_id:
        raise UserVisibleError(
            "This Bring Near session belongs to another document. Close it and start again."
        )

    if timeline["live_shot_id"] != shot_id:
        raise UserVisibleError(
            "Return to the shot where this Bring Near session started."
        )

    try:
        shot = sfmApp.GetShotAtCurrentTime()
    except Exception:
        shot = None

    if shot is None:
        raise RuntimeError(
            "live shot unavailable from modeless callback"
        )

    if _required_id(
        shot,
        "modeless live shot",
    ) != shot_id:
        raise RuntimeError(
            "modeless live shot identity mismatch"
        )

    return shot, timeline


def _capture_group_live_state(
    shot,
    reference_aset_id,
    target_aset_ids,
):
    owner_by_element_id, by_aset_id, all_records = (
        _build_owner_maps(shot)
    )

    reference = by_aset_id.get(
        reference_aset_id
    )

    if reference is None:
        raise UserVisibleError(
            "The Place near model or camera is no longer available."
        )

    if reference["kind"] not in (
        "MODEL",
        "CAMERA",
    ):
        raise RuntimeError(
            "captured reference type changed"
        )

    targets = []

    for aset_id in target_aset_ids:
        record = by_aset_id.get(aset_id)

        if record is None:
            raise UserVisibleError(
                "A model in this Bring Near group is no longer available."
            )

        if record["kind"] != "MODEL":
            raise RuntimeError(
                "captured target is no longer a model"
            )

        targets.append(record)

    resolved_targets = [
        _resolve_model_record(record)
        for record in targets
    ]

    reference_budget = [0]
    ordinary_budget = [0]
    blocked = []

    for record in targets:
        relationship = _target_relationship_state(
            record,
            owner_by_element_id,
            all_records,
            reference_budget,
            ordinary_budget,
        )

        if relationship["state"] != "FREE":
            blocked.append({
                "record": record,
                "relationship": relationship,
            })

    if blocked:
        raise UserVisibleError(
            _blocked_message(
                blocked
            )
        )

    ref_dag = _reference_dag(
        reference
    )
    ref_pos = _vec3(
        ref_dag.GetAbsPosition()
    )
    ref_q = _quat4(
        ref_dag.GetAbsOrientation()
    )
    ref_axes = _display_axes_from_quaternion(
        ref_dag.GetAbsOrientation()
    )

    if reference["kind"] == "MODEL":
        ref_bounds = _bounds_info(
            reference["element"]
        )
    else:
        ref_bounds = {
            "usable": False,
            "source": "camera",
            "mins": None,
            "maxs": None,
            "dims": None,
            "center": ref_pos,
        }

    target_geometry = []

    for resolved in resolved_targets:
        gm = resolved["gm"]
        parent_state = _optional_parent_state(
            gm
        )

        if not parent_state["complete"]:
            raise RuntimeError(
                "target parent state unreadable: %s"
                % _u(
                    resolved["record"][
                        "aset_info"
                    ]["name"]
                )
            )

        target_geometry.append({
            "resolved": resolved,
            "bounds": _bounds_info(gm),
            "root_pos": _vec3(
                gm.GetAbsPosition()
            ),
            "root_q": _quat4(
                gm.GetAbsOrientation()
            ),
            "parent_state": parent_state,
        })

    return {
        "reference": reference,
        "targets": targets,
        "resolved_targets": resolved_targets,
        "owner_by_element_id": owner_by_element_id,
        "all_records": all_records,
        "reference_dag": ref_dag,
        "reference_pos": ref_pos,
        "reference_q": ref_q,
        "reference_axes": ref_axes,
        "reference_bounds": ref_bounds,
        "target_geometry": target_geometry,
    }














# ===========================================================================
# Position writer and retained palette runtime
# ===========================================================================

BNP_APP_ATTR = "_chadchan3d_bnp_integrated_controller"
BNP_SESSION_UI_ATTR = "_chadchan3d_bnp_session_ui_state"
BNP_UNDO_NAME = "Bring Near Props"
BNP_REDO_NAME = "Redo Bring Near Props"
BNP_MOVE_STEP = 256.0
BNP_VECTOR_EPS = 0.05
BNP_TIME_EPS = 0.0001
BNP_MIN_PROVEN_MOVE = 32.0


_BNP_SUPPORT_LOG_MARKERS = set(
    (
        "WINDOW_CREATED",
        "MERGE_CAPTURE",
        "MODEL_REMOVED",
        "MODEL_REORDERED",
        "MODEL_NAME_ELIDED_UI",
        "MODEL_LIST_SIZING",
        "ARRANGEMENT_AXES",
        "SELECTION_UNRESOLVED_IGNORED",
        "SESSION_UI_STATE_SAVED",
        "SESSION_UI_STATE_RESTORED",
        "SESSION_UI_STATE_SAVE_SKIPPED",
        "SESSION_UI_STATE_RESTORE_SKIPPED",
        "GROUP_CLASSIFICATION_PASS",
        "APPLY_NOOP_ZERO_WRITES_ZERO_UNDO",
        "FRAME_ALIGNED_TIME_PREDICTION_PASS",
        "WHOLE_TRACK_POST_REFRESH",
        "APPLY_PASS",
        "APPLY_USER_BLOCK",
        "APPLY_EXCEPTION",
        "RECOVERY_REQUIRED",
        "RECOVERY_RECHECK_BLOCK",
        "RECOVERY_RECHECK_EXCEPTION",
        "RECOVERY_RECHECK_PASS_ZERO_WRITES",
        "SESSION_RETIRED",
        "WINDOW_CLOSE",
        "HOST_PREFLIGHT_BLOCK",
        "HOST_DESTROYED",
        "DOCUMENT_SWITCH_DETECTED_BEFORE_TIMELINE",
        "CONTROLLER_RETIRED_FOR_VERSION_CHANGE",
    )
)


def _bnp_log(marker, detail=None):
    if (
        marker not in _BNP_SUPPORT_LOG_MARKERS
        and not marker.startswith("PARTIAL_FAILURE_")
    ):
        return

    line = u"BNP_%s" % _u(marker)

    if detail is not None:
        line += u" detail=%s" % _u(detail)

    _append_log(
        [
            u"[%0.6f] %s"
            % (
                time.time(),
                line,
            )
        ]
    )


def _bnp_vec(value):
    return _vec3(value)


def _bnp_vec_obj(value):
    return vs.Vector(
        float(value[0]),
        float(value[1]),
        float(value[2]),
    )




def _bnp_time_seconds(value):
    try:
        return float(value.GetSeconds())
    except Exception:
        return None


def _bnp_frame_aligned_eval(state):
    """
    Read-only prediction of the channel time SFM will use at the current
    rendered frame.  No playhead/channel time is changed here.
    """
    current_time = state[
        "current_time"
    ]

    time_at_frame = getattr(
        current_time,
        "TimeAtCurrentFrame",
        None,
    )

    if not callable(
        time_at_frame
    ):
        raise UserVisibleError(
            "BNP could not access frame-aligned channel time."
        )

    framerate_type = getattr(
        vs,
        "DmeFramerate_t",
        None,
    )

    if framerate_type is None:
        raise UserVisibleError(
            "BNP could not access SFM's frame-rate type."
        )

    fps = float(
        sfmApp.GetFramesPerSecond()
    )

    if (
        not _finite_number(fps)
        or fps <= 0.0
    ):
        raise RuntimeError(
            "invalid SFM frame rate"
        )

    try:
        framerate = framerate_type(
            fps
        )
    except Exception:
        # Preserve generality for integer-rate projects without silently
        # approximating non-integer rates.
        nearest = int(
            round(
                fps
            )
        )

        if abs(
            fps - float(
                nearest
            )
        ) > 1.0e-6:
            raise UserVisibleError(
                "BNP could not construct SFM's frame-rate value."
            )

        framerate = framerate_type(
            nearest
        )

    aligned_time = time_at_frame(
        framerate
    )

    aligned_seconds = _bnp_time_seconds(
        aligned_time
    )

    if aligned_seconds is None:
        raise RuntimeError(
            "frame-aligned channel time unreadable"
        )

    aligned_evaluated = _bnp_vec(
        state[
            "log"
        ].GetValue(
            aligned_time
        )
    )

    return {
        "fps": fps,
        "time": aligned_time,
        "seconds": float(
            aligned_seconds
        ),
        "evaluated": aligned_evaluated,
    }


def _bnp_source_attribute(ctrl):
    # Engine-facing attribute names on this SFM/Python2 SWIG route must be
    # byte strings, not unicode.
    try:
        return ctrl.GetAttribute("valuePosition")
    except Exception:
        return None




BNP_MAX_KEYS = 32
BNP_EXACT_KEY_TIME_EPS = 0.000001


def _bnp_inventory(layer):
    count = int(
        layer.GetKeyCount()
    )

    if count < 1:
        raise UserVisibleError(
            "BNP requires at least one root position key."
        )

    if count > BNP_MAX_KEYS:
        raise UserVisibleError(
            "BNP test fixture has too many root position keys."
        )

    rows = []

    for index in range(count):
        key_time = layer.GetKeyTime(
            index
        )
        seconds = _bnp_time_seconds(
            key_time
        )

        if seconds is None:
            raise RuntimeError(
                "root position key time unreadable"
            )

        rows.append({
            "seconds": seconds,
            "value": _bnp_vec(
                layer.GetKeyValue(
                    index
                )
            ),
        })

    return rows


def _bnp_inventory_failures(
    expected,
    actual,
):
    failures = []

    if len(expected) != len(actual):
        return [
            "key count mismatch expected=%d actual=%d"
            % (
                len(expected),
                len(actual),
            )
        ]

    for index in range(
        len(expected)
    ):
        a = expected[index]
        b = actual[index]

        if abs(
            a["seconds"]
            - b["seconds"]
        ) > BNP_TIME_EPS:
            failures.append(
                "key %d time mismatch"
                % index
            )

        if not _bnp_vector_match(
            a["value"],
            b["value"],
        ):
            failures.append(
                "key %d value mismatch"
                % index
            )

    return failures


def _bnp_exact_key_indices(
    rows,
    seconds,
):
    return [
        index
        for index, row in enumerate(
            rows
        )
        if abs(
            row["seconds"]
            - seconds
        ) <= BNP_EXACT_KEY_TIME_EPS
    ]


def _bnp_binding_state(
    shot,
    target_aset_id,
):
    _, by_aset_id, _ = _build_owner_maps(
        shot
    )

    record = by_aset_id.get(
        target_aset_id
    )

    if (
        record is None
        or record["kind"] != "MODEL"
    ):
        raise RuntimeError(
            "captured BNP target is unavailable"
        )

    resolved = _resolve_model_record(
        record
    )

    gm = resolved["gm"]
    ctrl = resolved["ctrl"]
    transform = resolved["transform"]

    try:
        channel = ctrl.positionChannel
    except Exception:
        channel = None

    if channel is None:
        raise RuntimeError(
            "root positionChannel unavailable"
        )

    try:
        log = channel.log
    except Exception:
        log = None

    if log is None:
        raise RuntimeError(
            "root position log unavailable"
        )

    if int(
        log.GetNumLayers()
    ) != 1:
        raise UserVisibleError(
            "BNP requires exactly one root position log layer per target."
        )

    layer = log.GetLayer(0)

    if layer is None:
        raise RuntimeError(
            "root position layer 0 unavailable"
        )

    if int(
        log.GetKeyCount()
    ) != int(
        layer.GetKeyCount()
    ):
        raise RuntimeError(
            "log/layer key counts disagree"
        )

    inventory = _bnp_inventory(
        layer
    )

    current_time = channel.GetCurrentTime()
    current_seconds = _bnp_time_seconds(
        current_time
    )

    if current_seconds is None:
        raise RuntimeError(
            "channel current time unreadable"
        )

    source_attribute = _bnp_source_attribute(
        ctrl
    )

    if source_attribute is None:
        raise RuntimeError(
            "root valuePosition source attribute unavailable"
        )

    parent = _optional_parent_state(
        gm
    )

    if not parent["complete"]:
        raise RuntimeError(
            "target parent state unreadable"
        )

    return {
        "record": record,
        "resolved": resolved,
        "gm": gm,
        "ctrl": ctrl,
        "transform": transform,
        "channel": channel,
        "log": log,
        "layer": layer,
        "source_attribute": source_attribute,
        "current_time": current_time,
        "current_seconds": current_seconds,
        "inventory": inventory,
        "source": _bnp_vec(
            source_attribute.GetValue()
        ),
        "evaluated": _bnp_vec(
            log.GetValue(
                current_time
            )
        ),
        "destination": _bnp_vec(
            transform.GetPosition()
        ),
        "world": _bnp_vec(
            gm.GetAbsPosition()
        ),
        "q": _quat4(
            gm.GetAbsOrientation()
        ),
        "parent": parent,
        "ids": {
            "aset": resolved[
                "aset_id"
            ],
            "gm": resolved[
                "gm_id"
            ],
            "ctrl": resolved[
                "ctrl_id"
            ],
            "transform": resolved[
                "transform_id"
            ],
            "channel": _required_id(
                channel,
                "root position channel",
            ),
            "log": _required_id(
                log,
                "root position log",
            ),
            "layer": _required_id(
                layer,
                "root position layer",
            ),
        },
    }







def _bnp_selected_owner_ids(
    shot,
):
    _, _, owner_by_element_id = _build_owner_maps(
        shot
    )

    selection = _selected_owner_snapshot(
        owner_by_element_id
    )

    if selection[
        "unresolved"
    ] != 0:
        raise RuntimeError(
            "selection contains unresolved DAGs during BNP refresh probe"
        )

    return set(
        selection[
            "owner_ids"
        ]
    )


def _bnp_vector_match(
    a,
    b,
):
    return _distance(
        a,
        b,
    ) <= BNP_VECTOR_EPS


def _bnp_classify(
    state,
):
    rows = state[
        "inventory"
    ]

    if len(
        rows
    ) == 1:
        if abs(
            rows[0]["seconds"]
        ) > BNP_TIME_EPS:
            raise UserVisibleError(
                "This model uses an unsupported single-key position track."
            )

        baseline = rows[0][
            "value"
        ]

        for key in (
            "source",
            "evaluated",
            "destination",
            "world",
        ):
            if not _bnp_vector_match(
                baseline,
                state[
                    key
                ],
            ):
                raise UserVisibleError(
                    "This model's position state is not internally consistent."
                )

        return {
            "kind": "STATIC_CONSTANT",
            "key_index": 0,
        }

    baseline = state[
        "evaluated"
    ]

    for key in (
        "destination",
        "world",
    ):
        if not _bnp_vector_match(
            baseline,
            state[
                key
            ],
        ):
            raise UserVisibleError(
                "This model's current position state is not internally consistent."
            )

    return {
        "kind": "MULTI_KEY_TRANSLATE",
        "key_count": len(
            rows
        ),
    }




def _bnp_translation_inventory_failures(
    before,
    after,
    delta,
):
    failures = []

    if len(
        before
    ) != len(
        after
    ):
        return [
            "track key count changed expected=%d actual=%d"
            % (
                len(
                    before
                ),
                len(
                    after
                ),
            )
        ]

    for key_index in range(
        len(
            before
        )
    ):
        old = before[
            key_index
        ]
        new = after[
            key_index
        ]

        if abs(
            old[
                "seconds"
            ]
            - new[
                "seconds"
            ]
        ) > BNP_TIME_EPS:
            failures.append(
                "track key %d time changed"
                % key_index
            )
            continue

        expected = _add(
            old[
                "value"
            ],
            delta,
        )

        if not _bnp_vector_match(
            expected,
            new[
                "value"
            ],
        ):
            failures.append(
                "track key %d did not receive the uniform translation"
                % key_index
            )

    return failures


def _bnp_vector_text(
    value,
):
    return u"(%0.9f,%0.9f,%0.9f)" % (
        float(
            value[
                0
            ]
        ),
        float(
            value[
                1
            ]
        ),
        float(
            value[
                2
            ]
        ),
    )


def _bnp_whole_track_refresh_diagnostic(
    name,
    before,
    after,
    desired,
    frame_aligned_seconds,
    frame_aligned_evaluated,
):
    delta = _sub(
        desired,
        frame_aligned_evaluated,
    )

    inventory_failures = _bnp_translation_inventory_failures(
        before[
            "inventory"
        ],
        after[
            "inventory"
        ],
        delta,
    )

    current_before = float(
        before[
            "current_seconds"
        ]
    )
    current_after = float(
        after[
            "current_seconds"
        ]
    )

    residual_eval = _distance(
        after[
            "evaluated"
        ],
        desired,
    )
    residual_destination = _distance(
        after[
            "destination"
        ],
        desired,
    )
    residual_world = _distance(
        after[
            "world"
        ],
        desired,
    )

    _bnp_log(
        "WHOLE_TRACK_POST_REFRESH",
        u"name=%s time_before=%0.9f frame_aligned=%0.9f time_after=%0.9f time_delta=%0.9f "
        u"keys_uniform=%s desired=%s source=%s evaluated=%s destination=%s world=%s "
        u"residual_eval=%0.9f residual_destination=%0.9f residual_world=%0.9f"
        % (
            _u(
                name
            ),
            current_before,
            float(
                frame_aligned_seconds
            ),
            current_after,
            current_after - current_before,
            (
                u"yes"
                if not inventory_failures
                else u"no"
            ),
            _bnp_vector_text(
                desired
            ),
            _bnp_vector_text(
                after[
                    "source"
                ]
            ),
            _bnp_vector_text(
                after[
                    "evaluated"
                ]
            ),
            _bnp_vector_text(
                after[
                    "destination"
                ]
            ),
            _bnp_vector_text(
                after[
                    "world"
                ]
            ),
            residual_eval,
            residual_destination,
            residual_world,
        )
    )

    if inventory_failures:
        _bnp_log(
            "WHOLE_TRACK_POST_REFRESH_KEY_FAILURES",
            u"name=%s failures=%s"
            % (
                _u(
                    name
                ),
                u" | ".join(
                    _u(
                        failure
                    )
                    for failure in inventory_failures
                ),
            )
        )

    return {
        "inventory_failures": inventory_failures,
        "time_delta": current_after - current_before,
        "residual_eval": residual_eval,
        "residual_destination": residual_destination,
        "residual_world": residual_world,
    }


def _bnp_state_failures(
    expected,
    actual,
):
    failures = []

    for key in (
        "aset",
        "gm",
        "ctrl",
        "transform",
        "channel",
        "log",
        "layer",
    ):
        if (
            expected["ids"][
                key
            ]
            != actual["ids"][
                key
            ]
        ):
            failures.append(
                "identity changed: %s"
                % key
            )

    channel_delta = abs(
        expected[
            "current_seconds"
        ]
        - actual[
            "current_seconds"
        ]
    )

    expected_static = (
        len(
            expected[
                "inventory"
            ]
        ) == 1
        and abs(
            expected[
                "inventory"
            ][0][
                "seconds"
            ]
        ) <= BNP_TIME_EPS
    )
    actual_static = (
        len(
            actual[
                "inventory"
            ]
        ) == 1
        and abs(
            actual[
                "inventory"
            ][0][
                "seconds"
            ]
        ) <= BNP_TIME_EPS
    )

    if channel_delta > BNP_TIME_EPS:
        if (
            expected_static
            and actual_static
        ):
            _bnp_log(
                "STATIC_CHANNEL_TIME_DRIFT_IGNORED",
                u"expected=%.9f actual=%.9f delta=%.9f"
                % (
                    expected[
                        "current_seconds"
                    ],
                    actual[
                        "current_seconds"
                    ],
                    channel_delta,
                )
            )
        else:
            failures.append(
                "animated channel time changed"
            )

    failures.extend(
        _bnp_inventory_failures(
            expected[
                "inventory"
            ],
            actual[
                "inventory"
            ],
        )
    )

    for key in (
        "source",
        "evaluated",
        "destination",
        "world",
    ):
        if not _bnp_vector_match(
            expected[
                key
            ],
            actual[
                key
            ],
        ):
            failures.append(
                "%s mismatch"
                % key
            )

    if _qangle_deg(
        expected[
            "q"
        ],
        actual[
            "q"
        ],
    ) > VERIFY_ANG_DEG:
        failures.append(
            "orientation changed"
        )

    if not _same_optional_parent(
        expected[
            "parent"
        ],
        actual[
            "parent"
        ],
    ):
        failures.append(
            "parent changed"
        )

    return failures



BNP_MIN_MANUAL_MOVE = 32.0
BNP_MIN_MANUAL_ROTATE_DEG = 15.0








BNP_REQUIRED_RENAME = "ZZZ_BNP_Renamed"









BNP_ICON_PNG_BASE64 = (
    "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"
    "RK5CYII="
)

_BNP_WINDOW_ICON = None


def _bnp_window_icon():
    global _BNP_WINDOW_ICON

    if _BNP_WINDOW_ICON is not None:
        return _BNP_WINDOW_ICON

    try:
        raw = base64.b64decode(
            BNP_ICON_PNG_BASE64
        )

        pixmap = QtGui.QPixmap()

        if not pixmap.loadFromData(
            raw,
            "PNG"
        ):
            return None

        icon = QtGui.QIcon(
            pixmap
        )

        if icon.isNull():
            return None

        _BNP_WINDOW_ICON = icon
        return icon

    except Exception:
        return None


def _bnp_apply_window_icon(
    window,
):
    try:
        icon = _bnp_window_icon()

        if icon is not None:
            window.setWindowIcon(
                icon
            )
    except Exception:
        pass


BNP_SCRIPT_VERSION = u"1.0.0-rc50-grid-plane-controls"
BNP_MODAL_MS = 100
BNP_CONTEXT_MS = 250
BNP_LABEL_REFRESH_TICKS = 8


def _bnp_message(
    icon,
    text,
    title=u"Bring Near: Props",
):
    try:
        box = QtGui.QMessageBox()
        box.setWindowTitle(
            _u(
                title
            )
        )

        try:
            box.setWindowFlags(
                QtCore.Qt.Dialog
                | QtCore.Qt.WindowStaysOnTopHint
                | QtCore.Qt.WindowTitleHint
                | QtCore.Qt.WindowSystemMenuHint
                | QtCore.Qt.WindowCloseButtonHint
            )
            box.setModal(
                True
            )
        except Exception:
            pass

        _bnp_apply_window_icon(
            box
        )

        box.setIcon(
            icon
        )
        box.setTextFormat(
            QtCore.Qt.RichText
        )
        box.setText(
            _u(
                text
            )
        )
        box.setStandardButtons(
            QtGui.QMessageBox.Ok
        )

        try:
            font = QtGui.QApplication.font()
            if font.pointSize() < 11:
                font.setPointSize(
                    11
                )
            box.setFont(
                font
            )
            for child in box.findChildren(
                QtGui.QWidget
            ):
                child.setFont(
                    font
                )
        except Exception:
            pass

        box.exec_()
    except Exception:
        pass


def _bnp_warning(
    text,
):
    _bnp_message(
        QtGui.QMessageBox.Warning,
        text,
    )


def _bnp_info(
    text,
):
    try:
        dialog = QtGui.QDialog()
        dialog.setWindowTitle(
            "Bring Near: Props - Help"
        )

        try:
            dialog.setWindowFlags(
                QtCore.Qt.Dialog
                | QtCore.Qt.WindowStaysOnTopHint
                | QtCore.Qt.WindowTitleHint
                | QtCore.Qt.WindowSystemMenuHint
                | QtCore.Qt.WindowCloseButtonHint
            )
            dialog.setModal(
                True
            )
        except Exception:
            pass

        _bnp_apply_window_icon(
            dialog
        )

        dialog.resize(
            750,
            600,
        )

        layout = QtGui.QVBoxLayout(
            dialog
        )
        layout.setContentsMargins(
            16,
            16,
            16,
            14,
        )
        layout.setSpacing(
            12
        )

        label = QtGui.QLabel(
            _u(
                text
            )
        )
        label.setTextFormat(
            QtCore.Qt.RichText
        )
        label.setWordWrap(
            True
        )
        layout.addWidget(
            label
        )

        layout.addStretch(
            1
        )

        button_row = QtGui.QHBoxLayout()

        credit = QtGui.QLabel(
            u"License: CC0 \u00b7 Author: ChadChan3D"
        )
        button_row.addWidget(
            credit
        )

        button_row.addStretch(
            1
        )

        close_button = QtGui.QPushButton(
            "Close"
        )
        close_button.setMinimumWidth(
            72
        )
        close_button.clicked.connect(
            dialog.accept
        )
        button_row.addWidget(
            close_button
        )

        layout.addLayout(
            button_row
        )

        try:
            font = QtGui.QApplication.font()
            if font.pointSize() < 11:
                font.setPointSize(
                    11
                )
            dialog.setFont(
                font
            )
            for child in dialog.findChildren(
                QtGui.QWidget
            ):
                child.setFont(
                    font
                )
        except Exception:
            pass

        dialog.exec_()

    except Exception:
        pass


def _bnp_modal_description(
    widget,
):
    if widget is None:
        return u"None"

    try:
        title = _u(
            widget.windowTitle()
        )
    except Exception:
        title = u"<title-error>"

    try:
        class_name = _u(
            widget.metaObject().className()
        )
    except Exception:
        class_name = u"<class-error>"

    return u"title=%r class=%s" % (
        title,
        class_name,
    )


class BringNearPropsController(
    QtGui.QDialog
):
    def __init__(
        self,
        app,
        capture,
        host_window,
        host_meta,
        parent=None,
    ):
        QtGui.QDialog.__init__(
            self,
            parent,
        )

        self._app = app
        self._script_version = BNP_SCRIPT_VERSION

        self._host_window = host_window
        self._host_meta = dict(
            host_meta
        )
        self._host_alive = True
        self._host_generation = 1

        self._document_id = capture[
            "document_id"
        ]
        self._shot_id = capture[
            "shot_id"
        ]
        self._shot_name = capture[
            "shot_name"
        ]

        self._reference_id = capture[
            "reference_id"
        ]
        self._reference_name = capture[
            "reference_name"
        ]
        self._reference_kind = capture[
            "reference_kind"
        ]

        self._target_ids = list(
            capture[
                "target_ids"
            ]
        )
        self._target_names = list(
            capture[
                "target_names"
            ]
        )

        self._paused_for_shot = False
        self._retired = False
        self._retire_reason = None
        self._applying = False
        self._modal_active = False
        self._scene_suspended = False
        self._shutting_down = False
        self._scope_unresolved = False

        self._recovery_required = False
        self._recovery_pre = None
        self._recovery_target_ids = None
        self._recovery_target_names = None

        self._context_ticks = 0

        self._modal_timer = QtCore.QTimer(
            self
        )
        self._modal_timer.setInterval(
            BNP_MODAL_MS
        )
        self._modal_timer.timeout.connect(
            self._watch_modal
        )

        self._context_timer = QtCore.QTimer(
            self
        )
        self._context_timer.setInterval(
            BNP_CONTEXT_MS
        )
        self._context_timer.timeout.connect(
            self._watch_context
        )

        try:
            self._host_window.destroyed.connect(
                self._on_host_destroyed
            )
        except Exception:
            self._host_alive = False

        try:
            self._app.aboutToQuit.connect(
                self._on_about_to_quit
            )
        except Exception:
            pass

        self.setWindowTitle(
            "Bring Near: Props"
        )

        try:
            self.setWindowFlags(
                QtCore.Qt.Dialog
                | QtCore.Qt.WindowStaysOnTopHint
                | QtCore.Qt.WindowTitleHint
                | QtCore.Qt.WindowSystemMenuHint
                | QtCore.Qt.WindowCloseButtonHint
            )
            self.setWindowModality(
                QtCore.Qt.NonModal
            )
        except Exception:
            self.setModal(
                False
            )

        _bnp_apply_window_icon(
            self
        )

        self.setMinimumWidth(
            366
        )
        self.resize(
            366,
            550,
        )

        root = QtGui.QVBoxLayout(
            self
        )
        root.setContentsMargins(
            10,
            12,
            10,
            12,
        )
        root.setSpacing(
            9
        )

        self._reference_label = QtGui.QLabel()
        self._reference_label.setWordWrap(
            True
        )
        root.addWidget(
            self._reference_label
        )

        placement_group = QtGui.QGroupBox(
            "Where to place"
        )
        placement_layout = QtGui.QHBoxLayout(
            placement_group
        )
        placement_layout.setContentsMargins(
            10,
            14,
            10,
            10,
        )
        placement_layout.setSpacing(
            10
        )

        self._placement_buttons = {}

        for index, label in enumerate(
            PLACEMENTS
        ):
            button = QtGui.QRadioButton(
                label
            )
            self._placement_buttons[
                label
            ] = button
            placement_layout.addWidget(
                button
            )

            if index == 0:
                button.setChecked(
                    True
                )

        root.addWidget(
            placement_group
        )

        arrangement_group = QtGui.QGroupBox(
            "Arrangement"
        )
        arrangement_grid = QtGui.QGridLayout(
            arrangement_group
        )
        arrangement_grid.setContentsMargins(
            10,
            12,
            10,
            12,
        )
        arrangement_grid.setHorizontalSpacing(
            10
        )
        arrangement_grid.setVerticalSpacing(
            10
        )
        arrangement_grid.setColumnStretch(
            1,
            1,
        )

        arrangement_grid.addWidget(
            QtGui.QLabel(
                "Layout"
            ),
            0,
            0,
        )

        arrange_widget = QtGui.QWidget()
        arrange_layout = QtGui.QHBoxLayout(
            arrange_widget
        )
        arrange_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )
        arrange_layout.setSpacing(
            8
        )

        self._row_button = QtGui.QPushButton(
            "Row"
        )
        self._grid_button = QtGui.QPushButton(
            "Grid"
        )

        self._row_button.setCheckable(
            True
        )
        self._grid_button.setCheckable(
            True
        )
        self._row_button.setStyleSheet(
            ARRANGE_BUTTON_STYLE
        )
        self._grid_button.setStyleSheet(
            ARRANGE_BUTTON_STYLE
        )
        self._row_button.setChecked(
            True
        )

        self._arrange_group = QtGui.QButtonGroup(
            self
        )
        self._arrange_group.setExclusive(
            True
        )
        self._arrange_group.addButton(
            self._row_button
        )
        self._arrange_group.addButton(
            self._grid_button
        )

        arrange_layout.addWidget(
            self._row_button
        )
        arrange_layout.addWidget(
            self._grid_button
        )
        arrange_layout.addStretch(
            1
        )

        arrangement_grid.addWidget(
            arrange_widget,
            0,
            1,
        )

        self._direction_label = QtGui.QLabel(
            "Direction"
        )
        arrangement_grid.addWidget(
            self._direction_label,
            1,
            0,
        )

        self._direction = QtGui.QComboBox()
        self._direction.addItems(
            ROW_AXES
        )
        self._direction.setCurrentIndex(
            1
        )
        arrangement_grid.addWidget(
            self._direction,
            1,
            1,
        )

        self._secondary_direction_label = QtGui.QLabel(
            "Rows"
        )
        arrangement_grid.addWidget(
            self._secondary_direction_label,
            2,
            0,
        )

        self._secondary_direction = QtGui.QComboBox()
        arrangement_grid.addWidget(
            self._secondary_direction,
            2,
            1,
        )

        self._row_button.clicked.connect(
            self._arrangement_layout_changed
        )
        self._grid_button.clicked.connect(
            self._arrangement_layout_changed
        )
        self._direction.currentIndexChanged.connect(
            self._primary_direction_changed
        )

        self._refresh_secondary_direction_options(
            ROW_Z
        )
        self._sync_arrangement_controls()

        root.addWidget(
            arrangement_group
        )

        distances_group = QtGui.QGroupBox(
            "Distances"
        )
        distances_grid = QtGui.QGridLayout(
            distances_group
        )
        distances_grid.setContentsMargins(
            10,
            12,
            10,
            12,
        )
        distances_grid.setHorizontalSpacing(
            10
        )
        distances_grid.setVerticalSpacing(
            10
        )
        distances_grid.setColumnStretch(
            1,
            1,
        )

        self._from_reference_label = QtGui.QLabel(
            "From model"
        )
        distances_grid.addWidget(
            self._from_reference_label,
            0,
            0,
        )

        self._distance = StepValueWidget(
            DEFAULT_DISTANCE
        )
        distances_grid.addWidget(
            self._distance,
            0,
            1,
        )

        self._spacing_label = QtGui.QLabel(
            "Between models"
        )
        distances_grid.addWidget(
            self._spacing_label,
            1,
            0,
        )

        self._spacing = StepValueWidget(
            DEFAULT_SPACING
        )
        distances_grid.addWidget(
            self._spacing,
            1,
            1,
        )

        self._spacing_unavailable = QtGui.QLabel(
            "Requires 2+ models."
        )
        self._spacing_unavailable.setEnabled(
            False
        )
        self._spacing_unavailable.setVisible(
            False
        )
        distances_grid.addWidget(
            self._spacing_unavailable,
            1,
            1,
        )

        root.addWidget(
            distances_group
        )

        self._models_title = QtGui.QLabel()
        self._models_title.setTextFormat(
            QtCore.Qt.RichText
        )
        root.addWidget(
            self._models_title
        )

        self._models_scroll = QtGui.QScrollArea(
            self
        )
        self._models_scroll.setWidgetResizable(
            True
        )
        self._models_scroll.setFrameShape(
            QtGui.QFrame.NoFrame
        )
        self._models_scroll.setHorizontalScrollBarPolicy(
            QtCore.Qt.ScrollBarAlwaysOff
        )
        self._models_scroll.setVerticalScrollBarPolicy(
            QtCore.Qt.ScrollBarAsNeeded
        )
        self._models_scroll.setMinimumHeight(
            44
        )
        self._models_scroll.setMaximumHeight(
            300
        )
        self._models_scroll.setSizePolicy(
            QtGui.QSizePolicy.Expanding,
            QtGui.QSizePolicy.Fixed,
        )

        self._models_panel = QtGui.QWidget()
        self._models_layout = QtGui.QVBoxLayout(
            self._models_panel
        )
        self._models_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )
        self._models_layout.setSpacing(
            4
        )

        self._models_scroll.setWidget(
            self._models_panel
        )
        root.addWidget(
            self._models_scroll
        )

        self._status = QtGui.QLabel()
        self._status.setWordWrap(
            True
        )
        root.addWidget(
            self._status
        )

        self._recheck_button = QtGui.QPushButton(
            "Recheck after Ctrl+Z"
        )
        self._recheck_button.clicked.connect(
            self._recheck_recovery
        )
        self._recheck_button.setVisible(
            False
        )
        root.addWidget(
            self._recheck_button
        )

        root.addStretch(
            1
        )

        footer = QtGui.QHBoxLayout()
        footer.setSpacing(
            6
        )

        self._bring_button = QtGui.QPushButton(
            "Bring Near"
        )
        self._bring_button.setStyleSheet(
            BRING_BUTTON_STYLE
        )
        self._bring_button.setMinimumWidth(
            100
        )
        self._bring_button.clicked.connect(
            self._apply
        )

        help_button = QtGui.QPushButton(
            "Help"
        )
        help_button.clicked.connect(
            self._show_help
        )

        close_button = QtGui.QPushButton(
            "Close"
        )
        close_button.clicked.connect(
            self.close
        )

        footer.addStretch(
            1
        )
        footer.addWidget(
            self._bring_button
        )
        footer.addWidget(
            help_button
        )
        footer.addWidget(
            close_button
        )

        root.addLayout(
            footer
        )

        try:
            readable_font = QtGui.QApplication.font()
            if readable_font.pointSize() < 11:
                readable_font.setPointSize(
                    11
                )
            self.setFont(
                readable_font
            )
            for child in self.findChildren(
                QtGui.QWidget
            ):
                child.setFont(
                    readable_font
                )
        except Exception:
            pass

        self._restore_session_ui_state()
        self._refresh_reference_label()
        self._rebuild_models_panel()
        self._set_ready_status()
        self._refresh_controls()

        self._modal_timer.start()
        self._context_timer.start()

        _bnp_log(
            "WINDOW_CREATED",
            u"version=%s document=%s shot=%s reference=%s reference_id=%s targets=%s"
            % (
                self._script_version,
                self._document_id,
                self._shot_id,
                self._reference_name,
                self._reference_id,
                u" | ".join(
                    self._target_names
                ),
            )
        )

    def _session_ui_state(
        self,
    ):
        return {
            "placement": self._placement(),
            "layout": self._layout_mode(),
            "direction": _u(
                self._direction.currentText()
            ),
            "secondary_direction": _u(
                self._secondary_direction.currentText()
            ),
            "distance": int(
                self._distance.value()
            ),
            "spacing": int(
                self._spacing.value()
            ),
        }

    def _save_session_ui_state(
        self,
    ):
        try:
            state = self._session_ui_state()
            setattr(
                self._app,
                BNP_SESSION_UI_ATTR,
                dict(
                    state
                ),
            )

            _bnp_log(
                "SESSION_UI_STATE_SAVED",
                u"placement=%s layout=%s direction=%s secondary_direction=%s from=%d between=%d"
                % (
                    state["placement"],
                    state["layout"],
                    state["direction"],
                    state["secondary_direction"],
                    state["distance"],
                    state["spacing"],
                )
            )

        except Exception:
            _bnp_log(
                "SESSION_UI_STATE_SAVE_SKIPPED",
                _u(
                    traceback.format_exc()
                )
            )

    def _restore_session_ui_state(
        self,
    ):
        try:
            state = getattr(
                self._app,
                BNP_SESSION_UI_ATTR,
                None,
            )

            if not isinstance(
                state,
                dict,
            ):
                return

            placement = state.get(
                "placement"
            )

            if (
                placement in PLACEMENTS
                and placement in self._placement_buttons
            ):
                self._placement_buttons[
                    placement
                ].setChecked(
                    True
                )

            layout = state.get(
                "layout"
            )

            if layout == LAYOUT_GRID:
                self._grid_button.setChecked(
                    True
                )
            elif layout == LAYOUT_ROW:
                self._row_button.setChecked(
                    True
                )

            direction = _axis_choice_from_ui_text(
                state.get(
                    "direction",
                    u"",
                )
            )

            if direction is not None:
                direction_index = self._direction.findText(
                    direction
                )

                if direction_index >= 0:
                    self._direction.setCurrentIndex(
                        direction_index
                    )

            secondary_direction = _axis_choice_from_ui_text(
                state.get(
                    "secondary_direction",
                    u"",
                )
            )

            self._refresh_secondary_direction_options(
                secondary_direction
            )
            self._sync_arrangement_controls()

            try:
                distance = max(
                    1,
                    min(
                        INPUT_MAX,
                        int(
                            state.get(
                                "distance",
                                DEFAULT_DISTANCE,
                            )
                        ),
                    ),
                )
                self._distance._spin.setValue(
                    distance
                )
            except Exception:
                pass

            try:
                spacing = max(
                    1,
                    min(
                        INPUT_MAX,
                        int(
                            state.get(
                                "spacing",
                                DEFAULT_SPACING,
                            )
                        ),
                    ),
                )
                self._spacing._spin.setValue(
                    spacing
                )
            except Exception:
                pass

            restored = self._session_ui_state()

            _bnp_log(
                "SESSION_UI_STATE_RESTORED",
                u"placement=%s layout=%s direction=%s secondary_direction=%s from=%d between=%d"
                % (
                    restored["placement"],
                    restored["layout"],
                    restored["direction"],
                    restored["secondary_direction"],
                    restored["distance"],
                    restored["spacing"],
                )
            )

        except Exception:
            _bnp_log(
                "SESSION_UI_STATE_RESTORE_SKIPPED",
                _u(
                    traceback.format_exc()
                )
            )

    def script_version(
        self,
    ):
        return self._script_version

    def document_id(
        self,
    ):
        return self._document_id

    def shot_id(
        self,
    ):
        return self._shot_id

    def reference_id(
        self,
    ):
        return self._reference_id

    def retire_for_reload(
        self,
    ):
        if self._retired:
            return

        self._retired = True
        self._retire_reason = "SCRIPT_VERSION_REPLACED"


        try:
            self._context_timer.stop()
        except Exception:
            pass

        try:
            self._modal_timer.stop()
        except Exception:
            pass

        _bnp_log(
            "CONTROLLER_RETIRED_FOR_VERSION_CHANGE",
            u"version=%s reference_id=%s target_count=%d"
            % (
                self._script_version,
                self._reference_id,
                len(
                    self._target_ids
                ),
            )
        )

        try:
            self.close()
        except Exception:
            pass

    def _refresh_reference_label(
        self,
    ):
        kind = (
            "Camera"
            if self._reference_kind == "CAMERA"
            else
            "Model"
        )

        self._reference_label.setText(
            u"<b>Place models near:</b> %s <span style='color:#aaaaaa'>(%s)</span>"
            % (
                self._reference_name,
                kind,
            )
        )
        self._reference_label.setTextFormat(
            QtCore.Qt.RichText
        )

        self._from_reference_label.setText(
            "From camera"
            if self._reference_kind == "CAMERA"
            else "From model"
        )

    def _clear_models_layout(
        self,
    ):
        while self._models_layout.count():
            item = self._models_layout.takeAt(
                0
            )
            widget = item.widget()

            if widget is not None:
                widget.deleteLater()

    def _wanted_models_list_height(
        self,
        visible_row_cap=7,
    ):
        row_count = self._models_layout.count()

        if row_count <= 0:
            return 44

        visible_rows = min(
            int(
                visible_row_cap
            ),
            row_count,
        )

        margins = self._models_layout.contentsMargins()
        total = (
            margins.top()
            + margins.bottom()
        )

        spacing = max(
            0,
            int(
                self._models_layout.spacing()
            ),
        )

        measured_rows = 0

        for index in range(
            visible_rows
        ):
            item = self._models_layout.itemAt(
                index
            )

            if item is None:
                continue

            widget = item.widget()

            if widget is None:
                continue

            try:
                row_height = int(
                    widget.sizeHint().height()
                )
            except Exception:
                row_height = 0

            if row_height <= 0:
                try:
                    row_height = int(
                        widget.minimumSizeHint().height()
                    )
                except Exception:
                    row_height = 0

            if row_height <= 0:
                row_height = 30

            total += row_height
            measured_rows += 1

        if measured_rows > 1:
            total += spacing * (
                measured_rows - 1
            )

        # Small viewport slack avoids an unnecessary scrollbar caused by
        # one-pixel style/rounding differences.
        total += 2

        return max(
            44,
            min(
                300,
                int(
                    total
                ),
            ),
        )

    def _resize_for_model_count(
        self,
    ):
        row_count = len(
            self._target_ids
        )

        try:
            self._models_layout.activate()
            self._models_panel.adjustSize()
        except Exception:
            pass

        wanted_list_height = self._wanted_models_list_height(
            7
        )

        self._models_scroll.setMinimumHeight(
            wanted_list_height
        )
        self._models_scroll.setMaximumHeight(
            wanted_list_height
        )

        try:
            self.layout().activate()
        except Exception:
            pass

        try:
            ideal_height = int(
                self.sizeHint().height()
            )
        except Exception:
            ideal_height = 550

        try:
            desktop = QtGui.QApplication.desktop()
            available = desktop.availableGeometry(
                self
            )
            maximum_height = max(
                520,
                int(
                    available.height()
                ) - 80,
            )
        except Exception:
            available = None
            maximum_height = 900

        if ideal_height > maximum_height:
            overflow = ideal_height - maximum_height
            reduced_list_height = max(
                112,
                wanted_list_height - overflow,
            )

            self._models_scroll.setMinimumHeight(
                reduced_list_height
            )
            self._models_scroll.setMaximumHeight(
                reduced_list_height
            )

            try:
                self.layout().activate()
                ideal_height = int(
                    self.sizeHint().height()
                )
            except Exception:
                ideal_height = maximum_height

        final_height = min(
            maximum_height,
            max(
                460,
                ideal_height,
            ),
        )

        self.resize(
            366,
            final_height,
        )

        if available is not None:
            try:
                frame = self.frameGeometry()

                if frame.bottom() > available.bottom():
                    self.move(
                        self.x(),
                        max(
                            available.top(),
                            available.bottom()
                            - frame.height()
                            + 1,
                        ),
                    )
            except Exception:
                pass

        _bnp_log(
            "MODEL_LIST_SIZING",
            u"targets=%d normal_visible_cap=7 requested_list_height=%d actual_list_height=%d"
            % (
                row_count,
                wanted_list_height,
                int(
                    self._models_scroll.height()
                ),
            )
        )

        _bnp_log(
            "ADAPTIVE_WINDOW_SIZE",
            u"targets=%d list_height=%d window_width=%d window_height=%d max_height=%d"
            % (
                row_count,
                int(
                    self._models_scroll.height()
                ),
                int(
                    self.width()
                ),
                int(
                    self.height()
                ),
                maximum_height,
            )
        )

    def _rebuild_models_panel(
        self,
        availability=None,
        resize_window=True,
    ):
        self._clear_models_layout()

        self._models_title.setText(
            u"<b>Move these models (%d)</b>"
            % len(
                self._target_ids
            )
        )

        if not self._target_ids:
            empty = QtGui.QLabel(
                "Select models in the Animation Set Editor, then run the script again to add them."
            )
            empty.setWordWrap(
                True
            )
            self._models_layout.addWidget(
                empty
            )
            if resize_window:
                self._resize_for_model_count()
            return

        for index, (
            target_id,
            name,
        ) in enumerate(
            zip(
                self._target_ids,
                self._target_names,
            )
        ):
            row_widget = QtGui.QWidget(
                self._models_panel
            )

            if index % 2:
                try:
                    band_palette = row_widget.palette()
                    band_color = self.palette().color(
                        QtGui.QPalette.Window
                    ).lighter(
                        112
                    )
                    band_palette.setColor(
                        QtGui.QPalette.Window,
                        band_color,
                    )
                    row_widget.setPalette(
                        band_palette
                    )
                    row_widget.setAutoFillBackground(
                        True
                    )
                except Exception:
                    pass

            row = QtGui.QHBoxLayout(
                row_widget
            )
            row.setContentsMargins(
                4,
                2,
                4,
                2,
            )

            label_text = u"%d. %s" % (
                index + 1,
                name,
            )

            if (
                availability is not None
                and not availability.get(
                    target_id,
                    True,
                )
            ):
                label_text += u" (Unavailable)"

            label = ElidedModelNameLabel(
                label_text
            )
            row.addWidget(
                label,
                1,
            )

            up_button = QtGui.QPushButton(
                u"\u2191"
            )
            up_button.setFixedWidth(
                28
            )
            up_button.setToolTip(
                "Move up"
            )
            up_button.setProperty(
                "target_id",
                _u(
                    target_id
                ),
            )
            up_button.clicked.connect(
                self._move_up_clicked
            )
            up_button.setEnabled(
                index > 0
                and not self._applying
                and not self._recovery_required
                and not self._scope_unresolved
            )
            row.addWidget(
                up_button
            )

            down_button = QtGui.QPushButton(
                u"\u2193"
            )
            down_button.setFixedWidth(
                28
            )
            down_button.setToolTip(
                "Move down"
            )
            down_button.setProperty(
                "target_id",
                _u(
                    target_id
                ),
            )
            down_button.clicked.connect(
                self._move_down_clicked
            )
            down_button.setEnabled(
                index < len(
                    self._target_ids
                ) - 1
                and not self._applying
                and not self._recovery_required
                and not self._scope_unresolved
            )
            row.addWidget(
                down_button
            )

            remove_button = QtGui.QPushButton(
                "Remove"
            )
            remove_button.setFixedWidth(
                62
            )
            remove_button.setProperty(
                "target_id",
                _u(
                    target_id
                ),
            )
            remove_button.clicked.connect(
                self._remove_clicked
            )
            remove_button.setEnabled(
                not self._applying
                and not self._recovery_required
                and not self._scope_unresolved
            )
            row.addWidget(
                remove_button
            )

            self._models_layout.addWidget(
                row_widget
            )

        _bnp_log(
            "MODEL_NAME_ELIDED_UI",
            u"rows=%d"
            % (
                len(
                    self._target_ids
                ),
            )
        )

        if resize_window:
            self._resize_for_model_count()

    def _set_ready_status(
        self,
    ):
        if self._recovery_required:
            self._status.setText(
                "Recovery required. Press Ctrl+Z once, then click Recheck."
            )
            return

        if self._paused_for_shot:
            self._status.setText(
                u"Paused. Return to shot: %s"
                % self._shot_name
            )
            return

        if not self._target_ids:
            self._status.setText(
                ""
            )
            return

        self._status.setText(
            ""
        )

    def _refresh_controls(
        self,
    ):
        usable = (
            not self._retired
            and not self._shutting_down
            and not self._scope_unresolved
            and not self._recovery_required
            and not self._paused_for_shot
            and not self._applying
            and len(
                self._target_ids
            ) > 0
        )

        self._bring_button.setEnabled(
            usable
        )

        spacing_enabled = (
            len(
                self._target_ids
            ) >= 2
        )

        self._spacing.setVisible(
            spacing_enabled
        )
        self._spacing.setEnabled(
            spacing_enabled
        )
        self._spacing_label.setEnabled(
            spacing_enabled
        )
        self._spacing_unavailable.setVisible(
            not spacing_enabled
        )

        if spacing_enabled:
            self._single_target_ui_logged = False

        self._recheck_button.setVisible(
            self._recovery_required
        )
        self._recheck_button.setEnabled(
            self._recovery_required
            and not self._applying
            and not self._scope_unresolved
        )

        self._rebuild_models_panel()




    def _on_host_destroyed(
        self,
        *args
    ):
        self._host_alive = False
        self._host_generation += 1

        _bnp_log(
            "HOST_DESTROYED",
            u"host_generation=%d"
            % self._host_generation
        )



        # Return to the outer native event loop. No mouse move/drag,
        # repaint/update, ProcessEvents, history operation, or writer change.




    def _show_help(
        self,
    ):
        _bnp_info(
            u"<b>Start</b><br>"
            u"Select the models you want to use. Right-click the model or camera you want "
            u"the other models positioned around, then run the script.<br><br>"

            u"The item you right-click becomes the fixed point around which the other "
            u"selected models move. The other selected models are added under "
            u"<b>Move these models</b>.<br><br>"

            u"<b>Add more models</b><br>"
            u"To add more models, leave the main Bring Near window open. Select the models "
            u"in the Animation Set Editor, right-click one of those selected models, and "
            u"run the script again. Those models are added to <b>Move these models</b>.<br><br>"

            u"Adding models this way keeps the same fixed point. To change the fixed point, "
            u"close Bring Near. Then right-click and run the script again on the model or camera "
            u"you want to use as the new fixed point.<br><br>"

            u"<b>Where to place</b><br>"
            u"<b>In Front / Behind / Left / Right</b> chooses which side of the fixed point "
            u"the group moves to.<br>"
            u"<b>Layout</b> - Row places the models in a single line. Grid arranges them in "
            u"rows and columns.<br>"
            u"For <b>Row</b>, <b>Direction</b> chooses the axis the models spread along.<br>"
            u"For <b>Grid</b>, <b>Across</b> and <b>Rows</b> choose the two axes that form the grid plane.<br>"
            u"Axes are Front / Back (X), Left / Right (Y), and Up / Down (Z).<br>"
            u"<b>From model / From camera</b> sets how far the group is placed from the fixed point.<br>"
            u"<b>Between models</b> sets the spacing between models.<br>"
            u"Distances are measured from model root transforms.<br><br>"

            u"<b>Move these models</b><br>"
            u"This list shows which models will move. "
            u"Use <b>\u2191 / \u2193</b> to change their Row/Grid order. "
            u"Long names are shortened in the list; hover a name to see it in full. "
            u"Use <b>Remove</b> to take a model out of the group.<br><br>"

            u"<b>Movement only</b><br>"
            u"Bring Near moves model positions. Rotation, scale, and existing parenting are preserved."
        )


    def _placement(
        self,
    ):
        for label in PLACEMENTS:
            if self._placement_buttons[
                label
            ].isChecked():
                return label

        return PLACEMENT_FRONT

    def _layout_mode(
        self,
    ):
        return (
            LAYOUT_GRID
            if self._grid_button.isChecked()
            else LAYOUT_ROW
        )

    def _direction1(
        self,
    ):
        index = int(
            self._direction.currentIndex()
        )

        if index < 0 or index >= len(
            ROW_AXES
        ):
            raise RuntimeError(
                "unknown arrangement direction"
            )

        return ROW_AXES[
            index
        ]

    def _default_secondary_direction(
        self,
        first,
    ):
        if first in (
            ROW_X,
            ROW_Y,
        ):
            return ROW_Z

        if first == ROW_Z:
            if self._placement() in (
                PLACEMENT_FRONT,
                PLACEMENT_BEHIND,
            ):
                return ROW_Y

            return ROW_X

        raise RuntimeError(
            "could not resolve default grid direction"
        )

    def _refresh_secondary_direction_options(
        self,
        preferred=None,
    ):
        first = self._direction1()

        preferred_choice = _axis_choice_from_ui_text(
            preferred
        )

        if preferred_choice is None:
            preferred_choice = _axis_choice_from_ui_text(
                self._secondary_direction.currentText()
            )

        valid = [
            choice
            for choice in ROW_AXES
            if choice != first
        ]

        if preferred_choice not in valid:
            preferred_choice = self._default_secondary_direction(
                first
            )

        try:
            self._secondary_direction.blockSignals(
                True
            )
        except Exception:
            pass

        self._secondary_direction.clear()
        self._secondary_direction.addItems(
            valid
        )

        index = self._secondary_direction.findText(
            preferred_choice
        )

        if index < 0:
            index = 0

        self._secondary_direction.setCurrentIndex(
            index
        )

        try:
            self._secondary_direction.blockSignals(
                False
            )
        except Exception:
            pass

    def _sync_arrangement_controls(
        self,
    ):
        is_grid = (
            self._layout_mode()
            == LAYOUT_GRID
        )

        self._direction_label.setText(
            "Across"
            if is_grid
            else "Direction"
        )
        self._secondary_direction_label.setVisible(
            is_grid
        )
        self._secondary_direction.setVisible(
            is_grid
        )

    def _arrangement_layout_changed(
        self,
        *args
    ):
        if self._layout_mode() == LAYOUT_GRID:
            self._refresh_secondary_direction_options()

        self._sync_arrangement_controls()

        try:
            self._resize_for_model_count()
        except Exception:
            pass

    def _primary_direction_changed(
        self,
        *args
    ):
        self._refresh_secondary_direction_options()
        self._sync_arrangement_controls()

    def _direction2(
        self,
    ):
        if self._layout_mode() != LAYOUT_GRID:
            return None

        first = self._direction1()
        second = _axis_choice_from_ui_text(
            self._secondary_direction.currentText()
        )

        if second is None:
            raise RuntimeError(
                "unknown secondary arrangement direction"
            )

        if second == first:
            raise RuntimeError(
                "grid directions must be different"
            )

        return second

    def _foreign_modal(
        self,
    ):
        try:
            modal = QtGui.QApplication.activeModalWidget()
        except Exception:
            return None

        if modal is self:
            return None

        return modal

    def _suspend_scene_polling(
        self,
    ):
        if self._scene_suspended:
            return

        self._scene_suspended = True

        try:
            self._context_timer.stop()
        except Exception:
            pass

        _bnp_log(
            "SCENE_CONTEXT_POLL_SUSPENDED",
            u"context_timer_active=%s context_ticks=%d"
            % (
                _u(
                    self._context_timer.isActive()
                ),
                self._context_ticks,
            )
        )

    def _resume_scene_polling(
        self,
    ):
        if (
            not self._scene_suspended
            or self._retired
            or self._shutting_down
        ):
            return

        self._scene_suspended = False
        self._context_timer.start()

        _bnp_log(
            "SCENE_CONTEXT_POLL_RESUMED",
            u"context_timer_active=%s context_ticks=%d"
            % (
                _u(
                    self._context_timer.isActive()
                ),
                self._context_ticks,
            )
        )

    def _watch_modal(
        self,
    ):
        if (
            self._retired
            or self._shutting_down
        ):
            return

        modal = self._foreign_modal()

        if modal is not None:
            if not self._modal_active:
                self._modal_active = True

                # Qualified production contract: every scene/context watcher
                # stops before the stay-on-top palette yields to a foreign
                # modal dialog.
                self._suspend_scene_polling()

                description = _bnp_modal_description(
                    modal
                )

                self.hide()

                _bnp_log(
                    "MODAL_YIELD_HIDE",
                    u"palette_visible=%s %s"
                    % (
                        _u(
                            self.isVisible()
                        ),
                        description,
                    )
                )

            return

        if self._modal_active:
            self._modal_active = False

            # Restore without raise_() / activateWindow() so Bring Near does
            # not steal focus after the native modal closes.
            self.show()
            self._resume_scene_polling()

            _bnp_log(
                "MODAL_YIELD_RESTORE"
            )

    def _retire_document_session(
        self,
        reason,
        live_document_id=None,
    ):
        if self._retired:
            return

        self._retired = True
        self._retire_reason = reason


        try:
            self._context_timer.stop()
        except Exception:
            pass

        try:
            self._modal_timer.stop()
        except Exception:
            pass

        _bnp_log(
            "SESSION_RETIRED",
            u"reason=%s captured_document=%s live_document=%s"
            % (
                _u(
                    reason
                ),
                self._document_id,
                _u(
                    live_document_id
                ),
            )
        )

        if reason == "DOCUMENT_CHANGED":
            _bnp_log(
                "RESULT_PASS_INTEGRATED_DOCUMENT_SWITCH_RETIRE",
                u"captured_document=%s live_document=%s no_cross_document_timeline_resolution=True"
                % (
                    self._document_id,
                    _u(
                        live_document_id
                    ),
                )
            )

        try:
            self.close()
        except Exception:
            pass

    def _watch_context(
        self,
    ):
        if (
            self._retired
            or self._shutting_down
            or self._applying
            or self._scene_suspended
        ):
            return

        if self._foreign_modal() is not None:
            return

        self._context_ticks += 1

        # Document identity is the first scene-facing check. Do not ask for
        # timeline/shot state until the currently open document is proven to be
        # the document this Bring Near session belongs to.
        try:
            if not sfmApp.HasDocument():
                self._retire_document_session(
                    "NO_OPEN_DOCUMENT",
                    None,
                )
                return

            live_document = sfmApp.GetDocumentRoot()

            if live_document is None:
                self._retire_document_session(
                    "DOCUMENT_ROOT_UNAVAILABLE",
                    None,
                )
                return

            live_document_id = _required_id(
                live_document,
                "live document root",
            )

        except Exception:
            self._retire_document_session(
                "DOCUMENT_STATE_UNAVAILABLE",
                None,
            )
            return

        if live_document_id != self._document_id:
            _bnp_log(
                "DOCUMENT_SWITCH_DETECTED_BEFORE_TIMELINE",
                u"captured_document=%s live_document=%s no_cross_document_timeline_resolution=True"
                % (
                    self._document_id,
                    live_document_id,
                )
            )

            self._retire_document_session(
                "DOCUMENT_CHANGED",
                live_document_id,
            )
            return

        try:
            timeline = _timeline_snapshot()
        except Exception:
            self._retire_document_session(
                "TIMELINE_UNAVAILABLE",
                live_document_id,
            )
            return

        if timeline[
            "document_id"
        ] != self._document_id:
            raise RuntimeError(
                "document identity changed between identity check and timeline snapshot"
            )

        live_shot_id = timeline[
            "live_shot_id"
        ]

        if live_shot_id != self._shot_id:
            if not self._paused_for_shot:
                self._paused_for_shot = True
                self._set_ready_status()
                self._refresh_controls()

                _bnp_log(
                    "SHOT_PAUSED",
                    u"captured_shot=%s live_shot=%s"
                    % (
                        self._shot_id,
                        _u(
                            live_shot_id
                        ),
                    )
                )

            return

        if self._paused_for_shot:
            self._paused_for_shot = False

            try:
                shot, _ = _live_session_shot(
                    self._document_id,
                    self._shot_id,
                )
                _capture_group_live_state(
                    shot,
                    self._reference_id,
                    self._target_ids,
                )
                self._status.setText(
                    ""
                )

                _bnp_log(
                    "SHOT_RETURN_REVALIDATED",
                    u"reference_id=%s target_count=%d"
                    % (
                        self._reference_id,
                        len(
                            self._target_ids
                        ),
                    )
                )

            except UserVisibleError as exc:
                self._status.setText(
                    _u(
                        exc
                    )
                )

            except Exception:
                self._status.setText(
                    "Bring Near could not safely recheck the returned shot."
                )

            self._refresh_controls()

        if (
            self._context_ticks
            % BNP_LABEL_REFRESH_TICKS
            == 0
        ):
            self._refresh_live_labels()

    def _refresh_live_labels(
        self,
    ):
        if (
            self._paused_for_shot
            or self._scene_suspended
            or self._retired
            or self._shutting_down
        ):
            return

        try:
            shot, _ = _live_session_shot(
                self._document_id,
                self._shot_id,
            )
            _, by_aset_id, _ = _build_owner_maps(
                shot
            )

            reference = by_aset_id.get(
                self._reference_id
            )

            if reference is not None:
                self._reference_name = _u(
                    reference[
                        "aset_info"
                    ][
                        "name"
                    ]
                )
                self._refresh_reference_label()

            availability = {}

            for index, target_id in enumerate(
                self._target_ids
            ):
                record = by_aset_id.get(
                    target_id
                )

                if (
                    record is None
                    or record[
                        "kind"
                    ] != "MODEL"
                ):
                    availability[
                        target_id
                    ] = False
                    continue

                availability[
                    target_id
                ] = True
                self._target_names[
                    index
                ] = _u(
                    record[
                        "aset_info"
                    ][
                        "name"
                    ]
                )

            self._rebuild_models_panel(
                availability,
                False,
            )

        except Exception:
            pass

    def merge_from_rig_capture(
        self,
        merge_capture,
    ):
        if (
            self._retired
            or self._recovery_required
            or self._scope_unresolved
        ):
            raise UserVisibleError(
                "Finish the current Bring Near action before adding models."
            )

        existing_ids = set(
            self._target_ids
        )
        added = []

        for item in merge_capture[
            "models"
        ]:
            target_id = item[
                "id"
            ]

            if target_id == self._reference_id:
                continue

            if target_id in existing_ids:
                continue

            self._target_ids.append(
                target_id
            )
            self._target_names.append(
                item[
                    "name"
                ]
            )
            existing_ids.add(
                target_id
            )
            added.append(
                item[
                    "name"
                ]
            )

        self._rebuild_models_panel()
        self._set_ready_status()
        self._refresh_controls()

        if added:
            self._status.setText(
                u"Added %d model%s."
                % (
                    len(
                        added
                    ),
                    u"" if len(
                        added
                    ) == 1 else u"s",
                )
            )
        else:
            self._status.setText(
                "No new models were added."
            )

        _bnp_log(
            "MERGE_CAPTURE",
            u"invoking=%s added=%s final=%s reference=%s"
            % (
                _u(
                    merge_capture[
                        "invoking_name"
                    ]
                ),
                u" | ".join(
                    added
                ),
                u" | ".join(
                    self._target_names
                ),
                self._reference_name,
            )
        )

    def _move_up_clicked(
        self,
    ):
        sender = self.sender()
        target_id = _u(
            sender.property(
                "target_id"
            )
        )
        self._move_target_order(
            target_id,
            -1,
        )

    def _move_down_clicked(
        self,
    ):
        sender = self.sender()
        target_id = _u(
            sender.property(
                "target_id"
            )
        )
        self._move_target_order(
            target_id,
            1,
        )

    def _move_target_order(
        self,
        target_id,
        delta,
    ):
        if (
            self._applying
            or self._recovery_required
            or self._scope_unresolved
        ):
            return

        if target_id not in self._target_ids:
            return

        old_index = self._target_ids.index(
            target_id
        )
        new_index = old_index + int(
            delta
        )

        if (
            new_index < 0
            or new_index >= len(
                self._target_ids
            )
        ):
            return

        target_name = self._target_names[
            old_index
        ]

        self._target_ids[
            old_index
        ], self._target_ids[
            new_index
        ] = (
            self._target_ids[
                new_index
            ],
            self._target_ids[
                old_index
            ],
        )

        self._target_names[
            old_index
        ], self._target_names[
            new_index
        ] = (
            self._target_names[
                new_index
            ],
            self._target_names[
                old_index
            ],
        )

        self._rebuild_models_panel()
        self._set_ready_status()
        self._refresh_controls()

        _bnp_log(
            "MODEL_REORDERED",
            u"name=%s from=%d to=%d order=%s"
            % (
                target_name,
                old_index + 1,
                new_index + 1,
                u" | ".join(
                    self._target_names
                ),
            )
        )

    def _remove_clicked(
        self,
    ):
        if (
            self._applying
            or self._recovery_required
            or self._scope_unresolved
        ):
            return

        sender = self.sender()
        target_id = _u(
            sender.property(
                "target_id"
            )
        )

        if target_id not in self._target_ids:
            return

        index = self._target_ids.index(
            target_id
        )
        name = self._target_names[
            index
        ]

        del self._target_ids[
            index
        ]
        del self._target_names[
            index
        ]

        self._rebuild_models_panel()
        self._set_ready_status()
        self._refresh_controls()

        _bnp_log(
            "MODEL_REMOVED",
            u"name=%s id=%s remaining=%s"
            % (
                name,
                target_id,
                u" | ".join(
                    self._target_names
                ),
            )
        )

    def _capture_binding_batch(
        self,
        shot,
        ids=None,
    ):
        target_ids = (
            self._target_ids
            if ids is None
            else ids
        )

        return {
            target_id: _bnp_binding_state(
                shot,
                target_id,
            )
            for target_id in target_ids
        }

    def _batch_failures(
        self,
        expected,
        actual,
        ids,
        names,
    ):
        failures = []

        for target_id, name in zip(
            ids,
            names,
        ):
            sub = _bnp_state_failures(
                expected[
                    target_id
                ],
                actual[
                    target_id
                ],
            )

            for failure in sub:
                failures.append(
                    u"%s: %s"
                    % (
                        name,
                        failure,
                    )
                )

        return failures

    def _classify_batch(
        self,
        pre,
    ):
        classifications = {}

        for target_id, name in zip(
            self._target_ids,
            self._target_names,
        ):
            state = pre[
                target_id
            ]
            rows = state[
                "inventory"
            ]

            classification = _bnp_classify(
                state
            )
            classifications[
                target_id
            ] = classification

            if classification[
                "kind"
            ] == "MULTI_KEY_TRANSLATE":
                current_seconds = state[
                    "current_seconds"
                ]
                exact_count = len(
                    _bnp_exact_key_indices(
                        rows,
                        current_seconds,
                    )
                )

                frame_aligned = _bnp_frame_aligned_eval(
                    state
                )

                classification[
                    "frame_aligned_seconds"
                ] = frame_aligned[
                    "seconds"
                ]
                classification[
                    "frame_aligned_evaluated"
                ] = frame_aligned[
                    "evaluated"
                ]

                _bnp_log(
                    "WHOLE_TRACK_READY",
                    u"name=%s key_count=%d current=%0.9f frame_aligned=%0.9f "
                    u"time_delta=%0.9f fps=%0.9f exact_current_keys=%d "
                    u"current_eval=%s frame_eval=%s"
                    % (
                        _u(
                            name
                        ),
                        len(
                            rows
                        ),
                        current_seconds,
                        frame_aligned[
                            "seconds"
                        ],
                        frame_aligned[
                            "seconds"
                        ] - current_seconds,
                        frame_aligned[
                            "fps"
                        ],
                        exact_count,
                        _bnp_vector_text(
                            state[
                                "evaluated"
                            ]
                        ),
                        _bnp_vector_text(
                            frame_aligned[
                                "evaluated"
                            ]
                        ),
                    )
                )

        return classifications

    def _write_one(
        self,
        shot,
        target_id,
        name,
        before,
        classification,
        desired,
    ):
        live = _bnp_binding_state(
            shot,
            target_id,
        )

        if live[
            "ids"
        ] != before[
            "ids"
        ]:
            raise RuntimeError(
                "%s binding identity changed before mutation"
                % name
            )

        inventory_failures = _bnp_inventory_failures(
            before[
                "inventory"
            ],
            live[
                "inventory"
            ],
        )

        if inventory_failures:
            raise RuntimeError(
                "%s key inventory changed before mutation"
                % name
            )

        if classification[
            "kind"
        ] == "STATIC_CONSTANT":
            vector = _bnp_vec_obj(
                desired
            )

            live[
                "layer"
            ].SetKeyValue(
                0,
                vector,
            )
            live[
                "source_attribute"
            ].SetValue(
                vector
            )
            live[
                "channel"
            ].Operate()

            _bnp_log(
                "TARGET_WRITE_STATIC",
                u"name=%s"
                % name
            )

        elif classification[
            "kind"
        ] == "MULTI_KEY_TRANSLATE":
            frame_aligned_seconds = float(
                classification[
                    "frame_aligned_seconds"
                ]
            )
            frame_aligned_evaluated = classification[
                "frame_aligned_evaluated"
            ]

            delta = _sub(
                desired,
                frame_aligned_evaluated,
            )
            delta = _require_finite_tuple(
                delta,
                "frame-aligned whole-track translation delta",
            )

            immediate_expected = _add(
                before[
                    "evaluated"
                ],
                delta,
            )

            for key_index, row in enumerate(
                before[
                    "inventory"
                ]
            ):
                shifted = _add(
                    row[
                        "value"
                    ],
                    delta,
                )
                shifted = _require_finite_tuple(
                    shifted,
                    "shifted root-position key",
                )

                live[
                    "layer"
                ].SetKeyValue(
                    key_index,
                    _bnp_vec_obj(
                        shifted
                    ),
                )

            _bnp_log(
                "WHOLE_TRACK_WRITE",
                u"name=%s key_count=%d delta=(%0.6f,%0.6f,%0.6f) frame_basis=%0.9f exact_current_keys=%d"
                % (
                    _u(
                        name
                    ),
                    len(
                        before[
                            "inventory"
                        ]
                    ),
                    delta[
                        0
                    ],
                    delta[
                        1
                    ],
                    delta[
                        2
                    ],
                    frame_aligned_seconds,
                    len(
                        _bnp_exact_key_indices(
                            before[
                                "inventory"
                            ],
                            before[
                                "current_seconds"
                            ],
                        )
                    ),
                )
            )

            operate_seconds_before = float(
                sfmApp.GetHeadTimeInSeconds()
            )
            operate_frames_before = float(
                sfmApp.GetHeadTimeInFrames()
            )

            live[
                "channel"
            ].Operate()

            operate_seconds_after = float(
                sfmApp.GetHeadTimeInSeconds()
            )
            operate_frames_after = float(
                sfmApp.GetHeadTimeInFrames()
            )

            _bnp_log(
                "WHOLE_TRACK_CHANNEL_OPERATE",
                u"name=%s seconds_before=%0.9f seconds_after=%0.9f seconds_delta=%0.9f "
                u"frames_before=%0.9f frames_after=%0.9f frames_delta=%0.9f"
                % (
                    _u(
                        name
                    ),
                    operate_seconds_before,
                    operate_seconds_after,
                    operate_seconds_after - operate_seconds_before,
                    operate_frames_before,
                    operate_frames_after,
                    operate_frames_after - operate_frames_before,
                )
            )

            if abs(
                operate_seconds_after - operate_seconds_before
            ) > 0.0001:
                raise RuntimeError(
                    "%s channel Operate changed the playhead time"
                    % name
                )

        else:
            raise RuntimeError(
                "%s has unknown position-track classification"
                % name
            )

        immediate = _bnp_binding_state(
            shot,
            target_id,
        )

        if classification[
            "kind"
        ] == "STATIC_CONSTANT":
            if len(
                immediate[
                    "inventory"
                ]
            ) != 1:
                raise RuntimeError(
                    "%s static key count changed"
                    % name
                )

            if not _bnp_vector_match(
                immediate[
                    "inventory"
                ][
                    0
                ][
                    "value"
                ],
                desired,
            ):
                raise RuntimeError(
                    "%s static key value mismatch"
                    % name
                )

            for key in (
                "source",
                "evaluated",
                "destination",
                "world",
            ):
                if not _bnp_vector_match(
                    immediate[
                        key
                    ],
                    desired,
                ):
                    raise RuntimeError(
                        "%s static %s mismatch"
                        % (
                            name,
                            key,
                        )
                    )

        else:
            frame_aligned_seconds = float(
                classification[
                    "frame_aligned_seconds"
                ]
            )
            frame_aligned_evaluated = classification[
                "frame_aligned_evaluated"
            ]

            delta = _sub(
                desired,
                frame_aligned_evaluated,
            )

            immediate_expected = _add(
                before[
                    "evaluated"
                ],
                delta,
            )

            failures = _bnp_translation_inventory_failures(
                before[
                    "inventory"
                ],
                immediate[
                    "inventory"
                ],
                delta,
            )

            if failures:
                raise RuntimeError(
                    "%s whole-track translation failure: %s"
                    % (
                        name,
                        "; ".join(
                            failures
                        ),
                    )
                )

            if not _bnp_vector_match(
                immediate[
                    "source"
                ],
                before[
                    "source"
                ],
            ):
                raise RuntimeError(
                    "%s whole-track write changed source attribute"
                    % name
                )

            if not _bnp_vector_match(
                immediate[
                    "evaluated"
                ],
                immediate_expected,
            ):
                raise RuntimeError(
                    "%s translated track did not evaluate to the expected pre-render position"
                    % name
                )

            for key in (
                "destination",
                "world",
            ):
                if not _bnp_vector_match(
                    immediate[
                        key
                    ],
                    immediate_expected,
                ):
                    raise RuntimeError(
                        "%s channel Operate did not refresh %s to the expected pre-render position"
                        % (
                            name,
                            key,
                        )
                    )

            _bnp_log(
                "WHOLE_TRACK_OPERATE_VERIFY_PASS",
                u"name=%s expected_pre_render=%s destination=%s world=%s"
                % (
                    _u(
                        name
                    ),
                    _bnp_vector_text(
                        immediate_expected
                    ),
                    _bnp_vector_text(
                        immediate[
                            "destination"
                        ]
                    ),
                    _bnp_vector_text(
                        immediate[
                            "world"
                        ]
                    ),
                )
            )

            _bnp_log(
                "WHOLE_TRACK_VERIFY_PASS",
                u"name=%s key_count=%d"
                % (
                    _u(
                        name
                    ),
                    len(
                        immediate[
                            "inventory"
                        ]
                    ),
                )
            )

        if _qangle_deg(
            before[
                "q"
            ],
            immediate[
                "q"
            ],
        ) > VERIFY_ANG_DEG:
            raise RuntimeError(
                "%s orientation changed"
                % name
            )

        if not _same_optional_parent(
            before[
                "parent"
            ],
            immediate[
                "parent"
            ],
        ):
            raise RuntimeError(
                "%s parent changed"
                % name
            )


    def _apply(
        self,
    ):
        if not self._bring_button.isEnabled():
            return

        self._applying = True
        self._refresh_controls()

        scope_open = False
        notify_guard = None
        notify_scope_open = False
        mutation_started = False
        writes = 0
        cleanup_ok = False
        pre = None
        pre_ids = list(
            self._target_ids
        )
        pre_names = list(
            self._target_names
        )

        try:
            shot, _ = _live_session_shot(
                self._document_id,
                self._shot_id,
            )

            live_state = _capture_group_live_state(
                shot,
                self._reference_id,
                pre_ids,
            )

            layout_mode = self._layout_mode()
            direction1 = self._direction1()
            direction2 = self._direction2()

            _bnp_log(
                "ARRANGEMENT_AXES",
                u"layout=%s direction=%s secondary_direction=%s"
                % (
                    layout_mode,
                    direction1,
                    _u(
                        direction2
                    ),
                )
            )

            planning = _build_plans(
                live_state,
                self._placement(),
                layout_mode,
                direction1,
                direction2,
                self._distance.value(),
                self._spacing.value(),
            )

            plans = planning[
                "plans"
            ]

            _bnp_log(
                "LITERAL_LAYOUT_PLAN",
                u"requested_from=%0.3f actual_layout_origin_from=%0.3f requested_between=%0.3f "
                u"layout=%s target_count=%d"
                % (
                    float(
                        planning[
                            "minimum_distance"
                        ]
                    ),
                    float(
                        planning[
                            "actual_distance"
                        ]
                    ),
                    float(
                        planning[
                            "minimum_spacing"
                        ]
                    ),
                    _u(
                        planning[
                            "layout_mode"
                        ]
                    ),
                    len(
                        plans
                    ),
                )
            )

            for plan in plans:
                _bnp_log(
                    "LITERAL_LAYOUT_TARGET",
                    u"name=%s root_before=%s root_after=%s offset=%s"
                    % (
                        _u(
                            plan[
                                "name"
                            ]
                        ),
                        _bnp_vector_text(
                            plan[
                                "before_root"
                            ]
                        ),
                        _bnp_vector_text(
                            plan[
                                "destination_root"
                            ]
                        ),
                        _bnp_vector_text(
                            plan[
                                "layout_offset"
                            ]
                        ),
                    )
                )

            if len(
                plans
            ) != len(
                pre_ids
            ):
                raise RuntimeError(
                    "planner target count mismatch"
                )

            # _build_plans() stores target identity inside the qualified
            # resolved-model record. Bind destinations by that exact Animation
            # Set ID and fail closed if planner membership/order differs from
            # the captured group.
            desired_by_id = {}
            plan_ids = []

            for plan in plans:
                resolved = plan.get(
                    "resolved"
                )

                if resolved is None:
                    raise RuntimeError(
                        "planner result is missing resolved target identity"
                    )

                plan_id = resolved.get(
                    "aset_id"
                )

                if plan_id is None:
                    raise RuntimeError(
                        "planner result is missing target Animation Set ID"
                    )

                if plan_id in desired_by_id:
                    raise RuntimeError(
                        "planner returned duplicate target identity"
                    )

                desired_by_id[
                    plan_id
                ] = plan[
                    "destination_root"
                ]
                plan_ids.append(
                    plan_id
                )

            if plan_ids != pre_ids:
                raise RuntimeError(
                    "planner target identity/order mismatch"
                )

            _bnp_log(
                "PLAN_ID_BINDING_PASS",
                u"targets=%s"
                % u" | ".join(
                    plan_ids
                )
            )

            pre = self._capture_binding_batch(
                shot,
                pre_ids,
            )

            selected_owner_ids = _bnp_selected_owner_ids(
                shot
            )

            _bnp_log(
                "SELECTION_BASELINE",
                u"selection=%s"
                % u" | ".join(
                    sorted(
                        selected_owner_ids
                    )
                )
            )

            classifications = self._classify_batch(
                pre
            )

            changed_ids = []

            for target_id in pre_ids:
                desired = desired_by_id[
                    target_id
                ]
                distance = _distance(
                    pre[
                        target_id
                    ][
                        "world"
                    ],
                    desired,
                )

                if distance > NOOP_POS_EPS:
                    changed_ids.append(
                        target_id
                    )

            if not changed_ids:
                self._status.setText(
                    "Already in place."
                )
                _bnp_log(
                    "APPLY_NOOP_ZERO_WRITES_ZERO_UNDO",
                    u"target_count=%d"
                    % len(
                        pre_ids
                    )
                )
                return

            # Production integration: any changed target may be static or
            # animated.  Each animated target carries its own frame-aligned
            # evaluation snapshot; all changed targets share one native Undo
            # transaction and one application notification scope.
            probe_ids = [
                target_id
                for target_id in changed_ids
                if classifications[target_id]["kind"] == "MULTI_KEY_TRANSLATE"
            ]
            static_ids = [
                target_id
                for target_id in changed_ids
                if classifications[target_id]["kind"] == "STATIC_CONSTANT"
            ]

            if len(probe_ids) + len(static_ids) != len(changed_ids):
                raise RuntimeError(
                    "unsupported changed-target classification"
                )

            _bnp_log(
                "GROUP_CLASSIFICATION_PASS",
                u"changed=%d static=%d animated=%d"
                % (
                    len(
                        changed_ids
                    ),
                    len(
                        static_ids
                    ),
                    len(
                        probe_ids
                    ),
                )
            )

            vs.g_pDataModel.StartUndo(
                BNP_UNDO_NAME,
                BNP_REDO_NAME,
            )
            scope_open = True

            notify_state_before = bool(
                vs.g_pDataModel.IsSuppressingNotify()
            )

            notify_guard = vs.CAppNotifyScopeGuard(
                "Bring Near Props",
                0,
            )
            notify_scope_open = True

            _bnp_log(
                "APP_NOTIFY_SCOPE_OPEN",
                u"flags=0 suppressing_before=%r suppressing_during=%r"
                % (
                    notify_state_before,
                    bool(
                        vs.g_pDataModel.IsSuppressingNotify()
                    ),
                )
            )

            for target_id in changed_ids:
                index = pre_ids.index(
                    target_id
                )
                name = pre_names[
                    index
                ]

                mutation_started = True

                self._write_one(
                    shot,
                    target_id,
                    name,
                    pre[
                        target_id
                    ],
                    classifications[
                        target_id
                    ],
                    desired_by_id[
                        target_id
                    ],
                )

                writes += 1

            notify_guard.Release()
            notify_scope_open = False

            _bnp_log(
                "APP_NOTIFY_SCOPE_RELEASE",
                u"flags=0 suppressing_after=%r writes=%d"
                % (
                    bool(
                        vs.g_pDataModel.IsSuppressingNotify()
                    ),
                    writes,
                )
            )

            vs.g_pDataModel.FinishUndo()
            scope_open = False
            cleanup_ok = True

            refresh_before_seconds = float(
                sfmApp.GetHeadTimeInSeconds()
            )
            refresh_before_frames = float(
                sfmApp.GetHeadTimeInFrames()
            )

            self.setEnabled(
                False
            )
            try:
                sfmApp.ProcessEvents()
            finally:
                self.setEnabled(
                    True
                )

            refresh_after_seconds = float(
                sfmApp.GetHeadTimeInSeconds()
            )
            refresh_after_frames = float(
                sfmApp.GetHeadTimeInFrames()
            )

            _bnp_log(
                "NOTIFIED_REFRESH",
                u"seconds_before=%0.9f seconds_after=%0.9f seconds_delta=%0.9f "
                u"frames_before=%0.9f frames_after=%0.9f frames_delta=%0.9f"
                % (
                    refresh_before_seconds,
                    refresh_after_seconds,
                    refresh_after_seconds - refresh_before_seconds,
                    refresh_before_frames,
                    refresh_after_frames,
                    refresh_after_frames - refresh_before_frames,
                )
            )

            if abs(
                refresh_after_seconds - refresh_before_seconds
            ) > 0.0001:
                raise RuntimeError(
                    "playhead time changed during T108 baseline refresh"
                )

            for probe_id in probe_ids:
                probe_name = pre_names[
                    pre_ids.index(
                        probe_id
                    )
                ]

                post_render_state = _bnp_binding_state(
                    shot,
                    probe_id,
                )

                predicted_frame_time = classifications[
                    probe_id
                ][
                    "frame_aligned_seconds"
                ]

                if abs(
                    post_render_state[
                        "current_seconds"
                    ]
                    - predicted_frame_time
                ) > BNP_TIME_EPS:
                    raise RuntimeError(
                        "Rendered channel time did not match the predicted frame-aligned time"
                    )

                _bnp_log(
                    "FRAME_ALIGNED_TIME_PREDICTION_PASS",
                    u"name=%s predicted=%0.9f actual=%0.9f"
                    % (
                        _u(
                            probe_name
                        ),
                        predicted_frame_time,
                        post_render_state[
                            "current_seconds"
                        ],
                    )
                )

            post = self._capture_binding_batch(
                shot,
                pre_ids,
            )


            for target_id in pre_ids:
                desired = desired_by_id[
                    target_id
                ]
                classification = classifications[
                    target_id
                ]

                if classification[
                    "kind"
                ] == "MULTI_KEY_TRANSLATE":
                    index = pre_ids.index(
                        target_id
                    )
                    name = pre_names[
                        index
                    ]

                    diagnostic = _bnp_whole_track_refresh_diagnostic(
                        name,
                        pre[
                            target_id
                        ],
                        post[
                            target_id
                        ],
                        desired,
                        classification[
                            "frame_aligned_seconds"
                        ],
                        classification[
                            "frame_aligned_evaluated"
                        ],
                    )

                    if diagnostic[
                        "inventory_failures"
                    ]:
                        raise RuntimeError(
                            "post-refresh whole-track key inventory mismatch"
                        )

                for key in (
                    "evaluated",
                    "destination",
                    "world",
                ):
                    if not _bnp_vector_match(
                        post[
                            target_id
                        ][
                            key
                        ],
                        desired,
                    ):
                        if classification[
                            "kind"
                        ] == "MULTI_KEY_TRANSLATE":
                            raise RuntimeError(
                                "post-refresh translated track position mismatch"
                            )

                        raise RuntimeError(
                            "post-refresh target position mismatch"
                        )

            self._status.setText(
                u"Moved %d model%s."
                % (
                    len(
                        changed_ids
                    ),
                    u"" if len(
                        changed_ids
                    ) == 1 else u"s",
                )
            )

            _bnp_log(
                "APPLY_PASS",
                u"changed=%d total=%d"
                % (
                    len(
                        changed_ids
                    ),
                    len(
                        pre_ids
                    ),
                )
            )

        except UserVisibleError as exc:
            self._status.setText(
                _u(
                    exc
                )
            )
            _bnp_warning(
                _u(
                    exc
                )
            )

            _bnp_log(
                "APPLY_USER_BLOCK",
                _u(
                    exc
                )
            )

        except Exception:
            error_text = _u(
                traceback.format_exc()
            )

            _bnp_log(
                "APPLY_EXCEPTION",
                error_text,
            )

            if notify_scope_open and notify_guard is not None:
                try:
                    notify_guard.Release()
                    notify_scope_open = False

                    _bnp_log(
                        "PARTIAL_FAILURE_NOTIFY_SCOPE_RELEASE_PASS",
                        u"writes=%d mutation_started=%s"
                        % (
                            writes,
                            _u(
                                mutation_started
                            ),
                        )
                    )

                except Exception:
                    _bnp_log(
                        "PARTIAL_FAILURE_NOTIFY_SCOPE_RELEASE_FAIL",
                        _u(
                            traceback.format_exc()
                        )
                    )

            if scope_open:
                try:
                    vs.g_pDataModel.FinishUndo()
                    scope_open = False
                    cleanup_ok = True

                    _bnp_log(
                        "PARTIAL_FAILURE_FINISHUNDO_PASS",
                        u"writes=%d mutation_started=%s"
                        % (
                            writes,
                            _u(
                                mutation_started
                            ),
                        )
                    )

                except Exception:
                    cleanup_ok = False

                    _bnp_log(
                        "PARTIAL_FAILURE_FINISHUNDO_FAIL",
                        _u(
                            traceback.format_exc()
                        )
                    )

            if mutation_started and cleanup_ok and pre is not None:
                self._recovery_required = True
                self._recovery_pre = pre
                self._recovery_target_ids = pre_ids
                self._recovery_target_names = pre_names
                self._status.setText(
                    "Bring Near could not verify the move. Press Ctrl+Z once, then click Recheck."
                )
                _bnp_warning(
                    "Bring Near changed model positions but could not verify the final result.<br><br>"
                    "Press <b>Ctrl+Z once</b>, then click <b>Recheck after Ctrl+Z</b>."
                )

                _bnp_log(
                    "RECOVERY_REQUIRED",
                    u"writes=%d mutation_started=%s"
                    % (
                        writes,
                        _u(
                            mutation_started
                        ),
                    )
                )

            elif scope_open or (
                mutation_started
                and not cleanup_ok
            ):
                self._scope_unresolved = True
                self._status.setText(
                    "Bring Near could not close its Undo transaction safely. Restart SFM before continuing."
                )
                _bnp_warning(
                    "Bring Near could not finish safely.<br><br>"
                    "Restart Source Filmmaker before continuing."
                )

            else:
                self._status.setText(
                    "Bring Near could not complete. Nothing else was attempted."
                )
                _bnp_warning(
                    "Bring Near could not complete. Nothing else was attempted."
                )

        finally:
            self._applying = False
            self._refresh_controls()

    def _recheck_recovery(
        self,
    ):
        if not self._recovery_required:
            return

        try:
            shot, _ = _live_session_shot(
                self._document_id,
                self._shot_id,
            )

            current = self._capture_binding_batch(
                shot,
                self._recovery_target_ids,
            )

            failures = self._batch_failures(
                self._recovery_pre,
                current,
                self._recovery_target_ids,
                self._recovery_target_names,
            )

            if failures:
                self._status.setText(
                    "Recovery is not complete. Ctrl+Z must restore the pre-Apply state."
                )
                _bnp_warning(
                    "Recovery is not complete.<br><br>"
                    "The captured models are not back at their pre-Apply state."
                )

                _bnp_log(
                    "RECOVERY_RECHECK_BLOCK",
                    u" | ".join(
                        failures
                    )
                )
                return

            _capture_group_live_state(
                shot,
                self._reference_id,
                self._target_ids,
            )

            self._recovery_required = False
            self._recovery_pre = None
            self._recovery_target_ids = None
            self._recovery_target_names = None
            self._set_ready_status()

            _bnp_log(
                "RECOVERY_RECHECK_PASS_ZERO_WRITES"
            )

        except UserVisibleError as exc:
            self._status.setText(
                _u(
                    exc
                )
            )

        except Exception:
            self._status.setText(
                "Bring Near could not verify recovery."
            )
            _bnp_log(
                "RECOVERY_RECHECK_EXCEPTION",
                _u(
                    traceback.format_exc()
                )
            )

        self._refresh_controls()

    def _on_about_to_quit(
        self,
    ):
        if self._shutting_down:
            return

        self._shutting_down = True
        self._scene_suspended = True


        try:
            self._context_timer.stop()
        except Exception:
            pass

        try:
            self._modal_timer.stop()
        except Exception:
            pass

        try:
            if getattr(
                self._app,
                BNP_APP_ATTR,
                None,
            ) is self:
                setattr(
                    self._app,
                    BNP_APP_ATTR,
                    None,
                )
        except Exception:
            pass

        _bnp_log(
            "ABOUT_TO_QUIT_CLEANUP",
            u"scene_wrapper_deref_after_signal=False context_ticks=%d"
            % self._context_ticks
        )

    def closeEvent(
        self,
        event,
    ):

        self._save_session_ui_state()

        try:
            self._context_timer.stop()
        except Exception:
            pass

        try:
            self._modal_timer.stop()
        except Exception:
            pass

        _bnp_log(
            "WINDOW_CLOSE",
            u"retired=%s reason=%s recovery=%s unresolved=%s context_ticks=%d"
            % (
                _u(
                    self._retired
                ),
                _u(
                    self._retire_reason
                ),
                _u(
                    self._recovery_required
                ),
                _u(
                    self._scope_unresolved
                ),
                self._context_ticks,
            )
        )

        try:
            if getattr(
                self._app,
                BNP_APP_ATTR,
                None,
            ) is self:
                setattr(
                    self._app,
                    BNP_APP_ATTR,
                    None,
                )
        except Exception:
            pass

        try:
            event.accept()
        except Exception:
            pass


def _bnp_existing(
    app,
):
    try:
        return getattr(
            app,
            BNP_APP_ATTR,
            None,
        )
    except Exception:
        return None


def main():
    started = time.time()

    _append_log(
        [
            u"=" * 96,
            u"SFM BRING NEAR: PROPS",
            u"VERSION=1.0.0",
            u"INVOCATION_BEGIN timestamp=%0.6f"
            % started,
        ]
    )

    try:
        app = QtGui.QApplication.instance()

        if app is None:
            raise RuntimeError(
                "QApplication unavailable"
            )

        existing = _bnp_existing(
            app
        )

        if existing is not None:
            try:
                existing_version = existing.script_version()
            except Exception:
                existing_version = None

            if existing_version == BNP_SCRIPT_VERSION:
                merge_capture = _capture_merge_from_fresh_rig(
                    existing
                )

                existing.merge_from_rig_capture(
                    merge_capture
                )
                existing.show()
                existing.raise_()
                existing.activateWindow()

                _append_log(
                    [
                        u"INVOCATION_RESULT=MERGED_INTO_EXISTING_WINDOW",
                        u"PERF total_seconds=%.6f"
                        % _seconds_since(
                            started
                        ),
                    ]
                )
                return

            try:
                existing.retire_for_reload()
            except Exception:
                try:
                    existing.close()
                except Exception:
                    pass

        host_window, host_meta = _bnp_capture_verified_host(
            app
        )

        capture = _capture_initial_session()

        window = BringNearPropsController(
            app,
            capture,
            host_window,
            host_meta,
            None,
        )

        setattr(
            app,
            BNP_APP_ATTR,
            window,
        )

        window.show()
        window.raise_()
        window.activateWindow()

        _append_log(
            [
                u"INVOCATION_RESULT=NEW_WINDOW",
                u"WRITE_COUNT=0",
                u"PERF total_seconds=%.6f"
                % _seconds_since(
                    started
                ),
            ]
        )

    except UserVisibleError as exc:
        _append_log(
            [
                u"STATUS=USER_BLOCK",
                u"USER_MESSAGE=%s"
                % _u(
                    exc
                ),
            ]
        )
        _bnp_warning(
            _u(
                exc
            )
        )

    except Exception:
        _append_log(
            [
                u"STATUS=ERROR",
                _u(
                    traceback.format_exc()
                ),
            ]
        )
        _bnp_warning(
            "Bring Near could not open. Nothing changed."
        )


main()