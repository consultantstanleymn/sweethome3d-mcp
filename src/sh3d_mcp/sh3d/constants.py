"""Sweet Home 3D schema constants transcribed from docs/SCHEMA.md and the official DTD."""

CURRENT_VERSION = "5300"

DEFAULT_WALL_HEIGHT = 250.0
DEFAULT_WALL_THICKNESS = 7.5
DEFAULT_FLOOR_THICKNESS = 12.0

HOME_XML_ENTRY = "Home.xml"
LEGACY_HOME_ENTRY = "Home"
CONTENT_DIGESTS_ENTRY = "ContentDigests"

HOME_CHILD_ORDER: tuple[str, ...] = (
    "property",
    "furnitureVisibleProperty",
    "environment",
    "backgroundImage",
    "print",
    "compass",
    "camera",
    "observerCamera",
    "level",
    "pieceOfFurniture",
    "doorOrWindow",
    "furnitureGroup",
    "light",
    "wall",
    "room",
    "polyline",
    "dimensionLine",
    "label",
)

ROOM_CHILD_ORDER = ("property", "textStyle", "texture", "point")

KNOWN_TAGS: frozenset[str] = frozenset(
    {
        "home",
        "property",
        "furnitureVisibleProperty",
        "environment",
        "backgroundImage",
        "print",
        "printedLevel",
        "compass",
        "camera",
        "observerCamera",
        "level",
        "furnitureGroup",
        "pieceOfFurniture",
        "doorOrWindow",
        "sash",
        "light",
        "lightSource",
        "lightSourceMaterial",
        "shelfUnit",
        "shelf",
        "textStyle",
        "texture",
        "material",
        "transformation",
        "wall",
        "baseboard",
        "room",
        "point",
        "polyline",
        "dimensionLine",
        "label",
        "text",
    }
)

_FURNITURE_COMMON_ATTRS = frozenset(
    {
        "id",
        "name",
        "angle",
        "visible",
        "movable",
        "description",
        "information",
        "license",
        "creator",
        "modelMirrored",
        "nameVisible",
        "nameAngle",
        "nameXOffset",
        "nameYOffset",
        "price",
    }
)

_PIECE_OF_FURNITURE_COMMON_ATTRS = frozenset(
    {
        "level",
        "catalogId",
        "x",
        "y",
        "elevation",
        "width",
        "depth",
        "height",
        "dropOnTopElevation",
        "model",
        "icon",
        "planIcon",
        "modelRotation",
        "modelCenteredAtOrigin",
        "backFaceShown",
        "modelFlags",
        "modelSize",
        "doorOrWindow",
        "resizable",
        "deformable",
        "texturable",
        "staircaseCutOutShape",
        "color",
        "shininess",
        "valueAddedTaxPercentage",
        "currency",
    }
)

_PIECE_OF_FURNITURE_HORIZONTAL_ROTATION_ATTRS = frozenset(
    {
        "horizontallyRotatable",
        "pitch",
        "roll",
        "widthInPlan",
        "depthInPlan",
        "heightInPlan",
    }
)

_CAMERA_COMMON_ATTRS = frozenset(
    {
        "id",
        "name",
        "lens",
        "x",
        "y",
        "z",
        "yaw",
        "pitch",
        "time",
        "fieldOfView",
        "renderer",
    }
)

KNOWN_ATTRS: dict[str, frozenset[str]] = {
    "home": frozenset(
        {
            "version",
            "name",
            "camera",
            "selectedLevel",
            "wallHeight",
            "basePlanLocked",
            "furnitureSortedProperty",
            "furnitureDescendingSorted",
        }
    ),
    "property": frozenset({"name", "value", "type"}),
    "furnitureVisibleProperty": frozenset({"name"}),
    "environment": frozenset(
        {
            "groundColor",
            "backgroundImageVisibleOnGround3D",
            "skyColor",
            "lightColor",
            "wallsAlpha",
            "allLevelsVisible",
            "observerCameraElevationAdjusted",
            "ceillingLightColor",
            "drawingMode",
            "subpartSizeUnderLight",
            "photoWidth",
            "photoHeight",
            "photoAspectRatio",
            "photoQuality",
            "videoWidth",
            "videoAspectRatio",
            "videoQuality",
            "videoSpeed",
            "videoFrameRate",
        }
    ),
    "backgroundImage": frozenset(
        {
            "image",
            "scaleDistance",
            "scaleDistanceXStart",
            "scaleDistanceYStart",
            "scaleDistanceXEnd",
            "scaleDistanceYEnd",
            "xOrigin",
            "yOrigin",
            "visible",
        }
    ),
    "print": frozenset(
        {
            "headerFormat",
            "footerFormat",
            "planScale",
            "furniturePrinted",
            "planPrinted",
            "view3DPrinted",
            "paperWidth",
            "paperHeight",
            "paperTopMargin",
            "paperLeftMargin",
            "paperBottomMargin",
            "paperRightMargin",
            "paperOrientation",
        }
    ),
    "printedLevel": frozenset({"level"}),
    "compass": frozenset(
        {
            "x",
            "y",
            "diameter",
            "northDirection",
            "longitude",
            "latitude",
            "timeZone",
            "visible",
        }
    ),
    "camera": _CAMERA_COMMON_ATTRS | frozenset({"attribute"}),
    "observerCamera": _CAMERA_COMMON_ATTRS | frozenset({"attribute", "fixedSize"}),
    "level": frozenset(
        {
            "id",
            "name",
            "elevation",
            "floorThickness",
            "height",
            "elevationIndex",
            "visible",
            "viewable",
        }
    ),
    "furnitureGroup": _FURNITURE_COMMON_ATTRS
    | frozenset({"level", "x", "y", "elevation", "width", "depth", "height", "dropOnTopElevation"}),
    "pieceOfFurniture": (
        _FURNITURE_COMMON_ATTRS
        | _PIECE_OF_FURNITURE_COMMON_ATTRS
        | _PIECE_OF_FURNITURE_HORIZONTAL_ROTATION_ATTRS
    ),
    "doorOrWindow": _FURNITURE_COMMON_ATTRS
    | _PIECE_OF_FURNITURE_COMMON_ATTRS
    | frozenset(
        {
            "wallThickness",
            "wallDistance",
            "wallWidth",
            "wallLeft",
            "wallHeight",
            "wallTop",
            "wallCutOutOnBothSides",
            "widthDepthDeformable",
            "cutOutShape",
            "boundToWall",
        }
    ),
    "sash": frozenset({"xAxis", "yAxis", "width", "startAngle", "endAngle"}),
    "light": (
        _FURNITURE_COMMON_ATTRS
        | _PIECE_OF_FURNITURE_COMMON_ATTRS
        | _PIECE_OF_FURNITURE_HORIZONTAL_ROTATION_ATTRS
        | frozenset({"power"})
    ),
    "lightSource": frozenset({"x", "y", "z", "color", "diameter"}),
    "lightSourceMaterial": frozenset({"name"}),
    "shelfUnit": (
        _FURNITURE_COMMON_ATTRS
        | _PIECE_OF_FURNITURE_COMMON_ATTRS
        | _PIECE_OF_FURNITURE_HORIZONTAL_ROTATION_ATTRS
    ),
    "shelf": frozenset(
        {
            "elevation",
            "xLower",
            "yLower",
            "zLower",
            "xUpper",
            "yUpper",
            "zUpper",
        }
    ),
    "textStyle": frozenset({"attribute", "fontName", "fontSize", "bold", "italic", "alignment"}),
    "texture": frozenset(
        {
            "attribute",
            "catalogId",
            "name",
            "width",
            "height",
            "xOffset",
            "yOffset",
            "angle",
            "scale",
            "creator",
            "fittingArea",
            "leftToRightOriented",
            "image",
        }
    ),
    "material": frozenset({"name", "key", "color", "shininess"}),
    "transformation": frozenset({"name", "matrix"}),
    "wall": frozenset(
        {
            "id",
            "level",
            "wallAtStart",
            "wallAtEnd",
            "xStart",
            "yStart",
            "xEnd",
            "yEnd",
            "height",
            "heightAtEnd",
            "thickness",
            "arcExtent",
            "pattern",
            "topColor",
            "leftSideColor",
            "leftSideShininess",
            "rightSideColor",
            "rightSideShininess",
        }
    ),
    "baseboard": frozenset({"attribute", "thickness", "height", "color"}),
    "room": frozenset(
        {
            "id",
            "level",
            "name",
            "nameAngle",
            "nameXOffset",
            "nameYOffset",
            "areaVisible",
            "areaAngle",
            "areaXOffset",
            "areaYOffset",
            "floorVisible",
            "floorColor",
            "floorShininess",
            "ceilingVisible",
            "ceilingColor",
            "ceilingShininess",
            "ceilingFlat",
        }
    ),
    "point": frozenset({"x", "y"}),
    "polyline": frozenset(
        {
            "id",
            "level",
            "thickness",
            "capStyle",
            "joinStyle",
            "dashStyle",
            "dashPattern",
            "dashOffset",
            "startArrowStyle",
            "endArrowStyle",
            "elevation",
            "color",
            "closedPath",
        }
    ),
    "dimensionLine": frozenset(
        {
            "id",
            "level",
            "xStart",
            "yStart",
            "elevationStart",
            "xEnd",
            "yEnd",
            "elevationEnd",
            "offset",
            "endMarkSize",
            "angle",
            "color",
            "visibleIn3D",
        }
    ),
    "label": frozenset(
        {
            "id",
            "level",
            "x",
            "y",
            "angle",
            "elevation",
            "pitch",
            "color",
            "outlineColor",
        }
    ),
    "text": frozenset(),
}
