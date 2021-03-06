project(QtOpenGL)

set(QtOpenGL_SRC
${QtOpenGL_GEN_DIR}/qgl_wrapper.cpp
${QtOpenGL_GEN_DIR}/qglbuffer_wrapper.cpp
${QtOpenGL_GEN_DIR}/qglcolormap_wrapper.cpp
${QtOpenGL_GEN_DIR}/qglcontext_wrapper.cpp
${QtOpenGL_GEN_DIR}/qglformat_wrapper.cpp
${QtOpenGL_GEN_DIR}/qglframebufferobject_wrapper.cpp
${QtOpenGL_GEN_DIR}/qglframebufferobjectformat_wrapper.cpp
${QtOpenGL_GEN_DIR}/qglpixelbuffer_wrapper.cpp
${QtOpenGL_GEN_DIR}/qglshader_wrapper.cpp
${QtOpenGL_GEN_DIR}/qglshaderprogram_wrapper.cpp
${QtOpenGL_GEN_DIR}/qglwidget_wrapper.cpp
# module is always needed
${QtOpenGL_GEN_DIR}/qtopengl_module_wrapper.cpp
)

make_path(QtOpenGL_typesystem_path ${QtCore_SOURCE_DIR} ${QtGui_SOURCE_DIR} ${QtWidgets_SOURCE_DIR}
                                   ${QtCore_BINARY_DIR} ${QtGui_BINARY_DIR} ${QtWidgets_BINARY_DIR}
                                   ${QtOpenGL_SOURCE_DIR})

set(QtOpenGL_include_dirs   ${QtOpenGL_SOURCE_DIR}
                            ${Qt5Core_INCLUDE_DIRS}
                            ${Qt5Gui_INCLUDE_DIRS}
                            ${Qt5Widgets_INCLUDE_DIRS}
                            ${Qt5OpenGL_INCLUDE_DIRS}
                            ${SHIBOKEN_PYTHON_INCLUDE_DIR}
                            ${SHIBOKEN_INCLUDE_DIR}
                            ${libpyside_SOURCE_DIR}
                            ${QtWidgets_GEN_DIR}
                            ${QtGui_GEN_DIR}
                            ${QtCore_GEN_DIR}
                            ${QtOpenGL_GEN_DIR}
                            )
set(QtOpenGL_libraries      pyside2
                            ${SHIBOKEN_PYTHON_LIBRARIES}
                            ${Qt5Core_LIBRARIES}
                            ${Qt5Gui_LIBRARIES}
                            ${Qt5Widgets_LIBRARIES}
                            ${Qt5OpenGL_LIBRARIES})
set(QtOpenGL_deps QtWidgets)

create_pyside_module(QtOpenGL
                    QtOpenGL_include_dirs
                    QtOpenGL_libraries
                    QtOpenGL_deps
                    QtOpenGL_typesystem_path
                    QtOpenGL_SRC
                    "")
