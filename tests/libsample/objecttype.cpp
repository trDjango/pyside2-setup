/*
 * This file is part of the Shiboken Python Binding Generator project.
 *
 * Copyright (C) 2009 Nokia Corporation and/or its subsidiary(-ies).
 *
 * Contact: PySide team <contact@pyside.org>
 *
 * This program is free software; you can redistribute it and/or
 * modify it under the terms of the GNU Lesser General Public License
 * version 2.1 as published by the Free Software Foundation. Please
 * review the following information to ensure the GNU Lesser General
 * Public License version 2.1 requirements will be met:
 * http://www.gnu.org/licenses/old-licenses/lgpl-2.1.html.
 *
 * As a special exception to the GNU Lesser General Public License
 * version 2.1, the object code form of a "work that uses the Library"
 * may incorporate material from a header file that is part of the
 * Library.  You may distribute such object code under terms of your
 * choice, provided that the incorporated material (i) does not exceed
 * more than 5% of the total size of the Library; and (ii) is limited to
 * numerical parameters, data structure layouts, accessors, macros,
 * inline functions and templates.
 *
 * This program is distributed in the hope that it will be useful, but
 * WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public
 * License along with this program; if not, write to the Free Software
 * Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA
 * 02110-1301 USA
 */

#include "objecttype.h"
#include "objecttypelayout.h"
#include <algorithm>

using namespace std;

ObjectType::ObjectType(ObjectType* parent) : m_parent(0)
{
    setParent(parent);
}

ObjectType::~ObjectType()
{
    for (ObjectTypeList::iterator child_iter = m_children.begin();
         child_iter != m_children.end(); ++child_iter)
        delete *child_iter;
}

ObjectType*
ObjectType::createWithChild()
{
    ObjectType* parent = create();
    ObjectType* child = create();
    child->setObjectName("child");
    child->setParent(parent);
    return parent;
}

void
ObjectType::removeChild(ObjectType* child)
{
    if (!child)
        return;

    ObjectTypeList::iterator child_iter = std::find(m_children.begin(), m_children.end(), child);
    if (child_iter != m_children.end()) {
        m_children.erase(child_iter);
        child->m_parent = 0;
    }
}

ObjectType*
ObjectType::takeChild(ObjectType* child)
{
    if (!child)
        return 0;

    ObjectTypeList::iterator child_iter = std::find(m_children.begin(), m_children.end(), child);
    if (child_iter != m_children.end()) {
        m_children.erase(child_iter);
        child->m_parent = 0;
        return child;
    }
    return 0;
}

ObjectType*
ObjectType::takeChild(const Str& name)
{
    return takeChild(findChild(name));

}

ObjectType*
ObjectType::findChild(const Str& name)
{
    for (ObjectTypeList::iterator child_iter = m_children.begin();
         child_iter != m_children.end(); ++child_iter) {

        if ((*child_iter)->objectName() == name)
            return *child_iter;
    }
    return 0;
}

void
ObjectType::killChild(const Str& name)
{
    for (ObjectTypeList::iterator child_iter = m_children.begin();
         child_iter != m_children.end(); ++child_iter) {

        if ((*child_iter)->objectName() == name) {
            ObjectType* child = *child_iter;
            removeChild(child);
            delete child;
            break;
        }
    }
}

void
ObjectType::setParent(ObjectType* parent)
{
    if (m_parent == parent)
        return;

    if (m_parent)
        m_parent->removeChild(this);

    m_parent = parent;
    if (m_parent)
        m_parent->m_children.push_back(this);
}

void
ObjectType::setObjectName(const Str& name)
{
    m_objectName = name;
}

Str
ObjectType::objectName() const
{
    return m_objectName;
}

bool
ObjectType::causeEvent(Event::EventType eventType)
{
    Event e(eventType);
    return event(&e);
}

bool
ObjectType::event(Event* event)
{
    return true;
}

void ObjectType::setObjectLayout(ObjectTypeLayout* layout)
{
    layout->setParent(this);
    std::list<ObjectType*> objects = layout->objects();
    std::list<ObjectType*>::const_iterator it = objects.begin();
    for (; it != objects.end(); ++it)
        (*it)->setParent(this);
}

