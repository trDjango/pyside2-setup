project(QtQml)

set(QtQml_registerType "${QtQml_SOURCE_DIR}/pysideqmlregistertype.cpp")

set(QtQml_SRC
${QtQml_GEN_DIR}/qjsengine_wrapper.cpp
${QtQml_GEN_DIR}/qjsvalue_wrapper.cpp
${QtQml_GEN_DIR}/qjsvalueiterator_wrapper.cpp
${QtQml_GEN_DIR}/qqmlabstracturlinterceptor_wrapper.cpp
${QtQml_GEN_DIR}/qqmlapplicationengine_wrapper.cpp
${QtQml_GEN_DIR}/qqmlcomponent_wrapper.cpp
${QtQml_GEN_DIR}/qqmlcontext_wrapper.cpp
${QtQml_GEN_DIR}/qqmlerror_wrapper.cpp
${QtQml_GEN_DIR}/qqmldebuggingenabler_wrapper.cpp
${QtQml_GEN_DIR}/qqmlengine_wrapper.cpp
${QtQml_GEN_DIR}/qqmlexpression_wrapper.cpp
${QtQml_GEN_DIR}/qqmlextensioninterface_wrapper.cpp
${QtQml_GEN_DIR}/qqmltypesextensioninterface_wrapper.cpp
${QtQml_GEN_DIR}/qqmlextensionplugin_wrapper.cpp
${QtQml_GEN_DIR}/qqmlfile_wrapper.cpp
${QtQml_GEN_DIR}/qqmlfileselector_wrapper.cpp
${QtQml_GEN_DIR}/qqmlimageproviderbase_wrapper.cpp
${QtQml_GEN_DIR}/qqmlincubator_wrapper.cpp
${QtQml_GEN_DIR}/qqmlincubationcontroller_wrapper.cpp
#${QtQml_GEN_DIR}/qqmllistproperty_wrapper.cpp
${QtQml_GEN_DIR}/qqmllistreference_wrapper.cpp
${QtQml_GEN_DIR}/qqmlparserstatus_wrapper.cpp
${QtQml_GEN_DIR}/qqmlproperty_wrapper.cpp
${QtQml_GEN_DIR}/qqmlpropertymap_wrapper.cpp
${QtQml_GEN_DIR}/qqmlpropertyvaluesource_wrapper.cpp
${QtQml_GEN_DIR}/qqmlscriptstring_wrapper.cpp
${QtQml_GEN_DIR}/qqmlnetworkaccessmanagerfactory_wrapper.cpp
# module is always needed
${QtQml_GEN_DIR}/qtqml_module_wrapper.cpp
)

make_path(QtQml_typesystem_path ${QtCore_SOURCE_DIR} ${QtGui_SOURCE_DIR} ${QtNetwork_SOURCE_DIR}
                                ${QtCore_BINARY_DIR} ${QtGui_BINARY_DIR} ${QtNetwork_BINARY_DIR}
                                ${QtQml_SOURCE_DIR})

set(QtQml_include_dirs  ${QtQml_SOURCE_DIR}
                        ${Qt5Core_INCLUDE_DIRS}
                        ${Qt5Gui_INCLUDE_DIRS}
                        ${Qt5Network_INCLUDE_DIRS}
                        ${Qt5Qml_INCLUDE_DIRS}
                        ${SHIBOKEN_PYTHON_INCLUDE_DIR}
                        ${SHIBOKEN_INCLUDE_DIR}
                        ${libpyside_SOURCE_DIR}
                        ${QtGui_GEN_DIR}
                        ${QtCore_GEN_DIR}
                        ${QtNetwork_GEN_DIR}
                        ${QtQml_GEN_DIR})

set(QtQml_libraries pyside2
                    ${SHIBOKEN_PYTHON_LIBRARIES}
                    ${Qt5Core_LIBRARIES}
                    ${Qt5Gui_LIBRARIES}
                    ${Qt5Network_LIBRARIES}
                    ${Qt5Qml_LIBRARIES})

set(QtQml_deps QtGui QtNetwork)

create_pyside_module(QtQml
                     QtQml_include_dirs
                     QtQml_libraries
                     QtQml_deps
                     QtQml_typesystem_path
                     QtQml_SRC
                     QtQml_registerType)
