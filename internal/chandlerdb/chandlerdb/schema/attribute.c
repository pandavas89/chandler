/*
 *  Copyright (c) 2003-2006 Open Source Applications Foundation
 *
 *  Licensed under the Apache License, Version 2.0 (the "License");
 *  you may not use this file except in compliance with the License.
 *  You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 *  Unless required by applicable law or agreed to in writing, software
 *  distributed under the License is distributed on an "AS IS" BASIS,
 *  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *  See the License for the specific language governing permissions and
 *  limitations under the License.
 */


#include <Python.h>
#include "structmember.h"

#include "c.h"

static void t_attribute_dealloc(t_attribute *self);
static int t_attribute_traverse(t_attribute *self, visitproc visit, void *arg);
static int t_attribute_clear(t_attribute *self);
static PyObject *t_attribute_new(PyTypeObject *type,
                                 PyObject *args, PyObject *kwds);
static int t_attribute_init(t_attribute *self, PyObject *args, PyObject *kwds);

static PyObject *t_attribute_getAspect(t_attribute *self, PyObject *args);

static PyObject *t_attribute_invokeAfterChange(t_attribute *self,
                                               PyObject *args);

static PyObject *t_attribute__getCardinality(t_attribute *self, void *data);
static int t_attribute__setCardinality(t_attribute *self, t_values *values,
                                       void *data);
static PyObject *t_attribute__getRequired(t_attribute *self, void *data);
static int t_attribute__setRequired(t_attribute *self, PyObject *value,
                                    void *data);
static PyObject *t_attribute__getIndexed(t_attribute *self, void *data);
static int t_attribute__setIndexed(t_attribute *self, PyObject *value,
                                   void *data);
static PyObject *t_attribute__getNoInherit(t_attribute *self, void *data);
static int t_attribute__setNoInherit(t_attribute *self, PyObject *value,
                                     void *data);
static PyObject *t_attribute__getDefaultValue(t_attribute *self, void *data);
static int t_attribute__setDefaultValue(t_attribute *self, t_values *values,
                                        void *data);
static PyObject *t_attribute__getAfterChange(t_attribute *self, void *data);
static int t_attribute__setAfterChange(t_attribute *self, t_values *values,
                                       void *data);
static PyObject *t_attribute__getRedirectTo(t_attribute *self, void *data);
static int t_attribute__setRedirectTo(t_attribute *self, PyObject *value,
                                      void *data);
static PyObject *t_attribute__getOtherName(t_attribute *self, void *data);
static int t_attribute__setOtherName(t_attribute *self, t_values *values,
                                     void *data);
static PyObject *t_attribute__getTypeID(t_attribute *self, void *data);
static int t_attribute__setTypeID(t_attribute *self, t_values *refs,
                                  void *data);
static PyObject *t_attribute__getProcess(t_attribute *self, void *data);

static PyObject *_getRef_NAME;
static PyObject *getFlags_NAME;
static PyObject *cardinality_NAME;
static PyObject *single_NAME, *list_NAME, *dict_NAME, *set_NAME;
static PyObject *required_NAME;
static PyObject *indexed_NAME;
static PyObject *otherName_NAME;
static PyObject *redirectTo_NAME;
static PyObject *inheritFrom_NAME;
static PyObject *defaultValue_NAME;
static PyObject *afterChange_NAME;
static PyObject *type_NAME;

static PyMemberDef t_attribute_members[] = {
    { "attrID", T_OBJECT, offsetof(t_attribute, attrID), READONLY,
      "attribute uuid" },
    { "flags", T_INT, offsetof(t_attribute, flags), 0,
      "attribute flags" },
    { NULL, 0, 0, 0, NULL }
};

static PyMethodDef t_attribute_methods[] = {
    { "getAspect", (PyCFunction) t_attribute_getAspect, METH_VARARGS, "" },
    { "invokeAfterChange", (PyCFunction) t_attribute_invokeAfterChange, METH_VARARGS, "" },
    { NULL, NULL, 0, NULL }
};

static PyGetSetDef t_attribute_properties[] = {
    { "cardinality",
      (getter) t_attribute__getCardinality,
      (setter) t_attribute__setCardinality,
      "cardinality property", NULL },
    { "required",
      (getter) t_attribute__getRequired,
      (setter) t_attribute__setRequired,
      "required property", NULL },
    { "indexed",
      (getter) t_attribute__getIndexed,
      (setter) t_attribute__setIndexed,
      "indexed property", NULL },
    { "noInherit",
      (getter) t_attribute__getNoInherit,
      (setter) t_attribute__setNoInherit,
      "noInherit property", NULL },
    { "defaultValue",
      (getter) t_attribute__getDefaultValue,
      (setter) t_attribute__setDefaultValue,
      "defaultValue property", NULL },
    { "afterChange",
      (getter) t_attribute__getAfterChange,
      (setter) t_attribute__setAfterChange,
      "afterChange property", NULL },
    { "redirectTo",
      (getter) t_attribute__getRedirectTo,
      (setter) t_attribute__setRedirectTo,
      "redirectTo property", NULL },
    { "otherName",
      (getter) t_attribute__getOtherName,
      (setter) t_attribute__setOtherName,
      "otherName property", NULL },
    { "typeID",
      (getter) t_attribute__getTypeID,
      (setter) t_attribute__setTypeID,
      "typeID property", NULL },
    { "process",
      (getter) t_attribute__getProcess,
      NULL,
      "process property", NULL },
    { NULL, NULL, NULL, NULL, NULL }
};

static PyTypeObject AttributeType = {
    PyObject_HEAD_INIT(NULL)
    0,                                          /* ob_size */
    "chandlerdb.schema.c.CAttribute",           /* tp_name */
    sizeof(t_attribute),                        /* tp_basicsize */
    0,                                          /* tp_itemsize */
    (destructor)t_attribute_dealloc,            /* tp_dealloc */
    0,                                          /* tp_print */
    0,                                          /* tp_getattr */
    0,                                          /* tp_setattr */
    0,                                          /* tp_compare */
    0,                                          /* tp_repr */
    0,                                          /* tp_as_number */
    0,                                          /* tp_as_sequence */
    0,                                          /* tp_as_mapping */
    0,                                          /* tp_hash  */
    0,                                          /* tp_call */
    0,                                          /* tp_str */
    0,                                          /* tp_getattro */
    0,                                          /* tp_setattro */
    0,                                          /* tp_as_buffer */
    (Py_TPFLAGS_DEFAULT |
     Py_TPFLAGS_BASETYPE |
     Py_TPFLAGS_HAVE_GC),                       /* tp_flags */
    "attribute",                                /* tp_doc */
    (traverseproc)t_attribute_traverse,         /* tp_traverse */
    (inquiry)t_attribute_clear,                 /* tp_clear */
    0,                                          /* tp_richcompare */
    0,                                          /* tp_weaklistoffset */
    0,                                          /* tp_iter */
    0,                                          /* tp_iternext */
    t_attribute_methods,                        /* tp_methods */
    t_attribute_members,                        /* tp_members */
    t_attribute_properties,                     /* tp_getset */
    0,                                          /* tp_base */
    0,                                          /* tp_dict */
    0,                                          /* tp_descr_get */
    0,                                          /* tp_descr_set */
    0,                                          /* tp_dictoffset */
    (initproc)t_attribute_init,                 /* tp_init */
    0,                                          /* tp_alloc */
    (newfunc)t_attribute_new,                   /* tp_new */
};


static void t_attribute_dealloc(t_attribute *self)
{
    t_attribute_clear(self);
    self->ob_type->tp_free((PyObject *) self);
}

static int t_attribute_traverse(t_attribute *self, visitproc visit, void *arg)
{
    Py_VISIT(self->attrID);
    Py_VISIT(self->otherName);
    Py_VISIT(self->redirectTo);
    Py_VISIT(self->defaultValue);
    Py_VISIT(self->typeID);
    Py_VISIT(self->afterChange);

    return 0;
}

static int t_attribute_clear(t_attribute *self)
{
    Py_CLEAR(self->attrID);
    Py_CLEAR(self->otherName);
    Py_CLEAR(self->redirectTo);
    Py_CLEAR(self->defaultValue);
    Py_CLEAR(self->typeID);
    Py_CLEAR(self->afterChange);

    return 0;
}


static PyObject *t_attribute_new(PyTypeObject *type,
                                 PyObject *args, PyObject *kwds)
{
    t_attribute *self = (t_attribute *) type->tp_alloc(type, 0);

    if (self)
    {
        self->attrID = NULL;
        self->otherName = NULL;
        self->redirectTo = NULL;
        self->defaultValue = NULL;
        self->typeID = NULL;
        self->afterChange = NULL;
    }

    return (PyObject *) self;
}

static int t_attribute_init(t_attribute *self, PyObject *args, PyObject *kwds)
{
    PyObject *attribute;

    if (!PyArg_ParseTuple(args, "O", &attribute))
        return -1;
    else
    {
        t_values *values = ((t_item *) attribute)->values;
        PyObject *dict = values->dict;
        PyObject *cardinality = PyDict_GetItem(dict, cardinality_NAME);
        PyObject *inheritFrom = PyDict_GetItem(dict, inheritFrom_NAME);
        PyObject *defaultValue = PyDict_GetItem(dict, defaultValue_NAME);
        PyObject *redirectTo = PyDict_GetItem(dict, redirectTo_NAME);
        PyObject *afterChange = PyDict_GetItem(dict, afterChange_NAME);
        int flags = NOINHERIT;

        if (!cardinality)
            flags |= SINGLE;
        else if (!PyObject_Compare(cardinality, single_NAME))
            flags |= SINGLE;
        else if (!PyObject_Compare(cardinality, list_NAME))
            flags |= LIST;
        else if (!PyObject_Compare(cardinality, dict_NAME))
            flags |= DICT;
        else if (!PyObject_Compare(cardinality, set_NAME))
            flags |= SET;

        if (PyDict_GetItem(dict, required_NAME) == Py_True)
            flags |= REQUIRED;

        if (PyDict_GetItem(dict, indexed_NAME) == Py_True)
            flags |= INDEXED;

        if (inheritFrom != NULL && inheritFrom != Py_None)
            flags &= ~NOINHERIT;

        if (defaultValue != NULL)
        {
            flags |= DEFAULT;
            Py_INCREF(defaultValue);
            self->defaultValue = defaultValue;
        }

        if (afterChange != NULL)
        {
            flags |= AFTERCHANGE;
            Py_INCREF(afterChange);
            self->afterChange = afterChange;
        }

        if (redirectTo != NULL && redirectTo != Py_None)
        {
            flags |= REDIRECT | PROCESS;
            flags &= ~NOINHERIT;

            Py_INCREF(redirectTo);
            self->redirectTo = redirectTo;
        }
        else
        {
            PyObject *otherName = PyDict_GetItem(dict, otherName_NAME);

            if (otherName != NULL && otherName != Py_None)
            {
                if (flags & SINGLE)
                    flags |= PROCESS;

                flags |= REF;

                Py_INCREF(otherName);
                self->otherName = otherName;
            }
        }

        if (!(flags & (REF | REDIRECT)))
        {
            t_values *references = ((t_item *) attribute)->references;

            if (PyDict_Contains(references->dict, type_NAME))
            {
                PyObject *type = PyObject_CallMethodObjArgs((PyObject *) references, _getRef_NAME, type_NAME, Py_None, Py_None, NULL);

                if (type == NULL)
                    return -1;

                if (type == Py_None)
                    self->typeID = type;
                else if (!PyObject_TypeCheck(type, CItem))
                {
                    PyErr_SetObject(PyExc_TypeError, type);
                    Py_DECREF(type);
                    return -1;
                }
                else
                {
                    PyObject *typeFlags =
                        PyObject_CallMethodObjArgs(type, getFlags_NAME, NULL);
                    PyObject *uuid = ((t_item *) type)->ref->uuid;

                    Py_INCREF(uuid);
                    self->typeID = uuid;

                    Py_DECREF(type);

                    if (typeFlags == NULL)
                        return -1;

                    if (!PyInt_Check(typeFlags))
                    {
                        PyErr_SetObject(PyExc_TypeError, typeFlags);
                        Py_DECREF(typeFlags);

                        return -1;
                    }

                    flags |= PyInt_AsLong(typeFlags);
                    Py_DECREF(typeFlags);
                }
            }
            else
                flags |= PROCESS;

            flags |= VALUE;
        }

        self->flags = flags;
        self->attrID = ((t_item *) attribute)->ref->uuid;
        Py_INCREF(self->attrID);

        return 0;
    }
}

static PyObject *t_attribute_getAspect(t_attribute *self, PyObject *args)
{
    PyObject *aspect, *defaultValue;

    if (!PyArg_ParseTuple(args, "OO", &aspect, &defaultValue))
        return NULL;
    else
    {
        int flags = self->flags;
                    
        if (!(flags & REDIRECT))
        {
            if (!PyObject_Compare(aspect, redirectTo_NAME))
                Py_RETURN_NONE;

            else if (!PyObject_Compare(aspect, cardinality_NAME))
                return t_attribute__getCardinality(self, NULL);

            else if (!PyObject_Compare(aspect, otherName_NAME))
            {
                if (flags & REF)
                {
                    Py_INCREF(self->otherName);
                    return self->otherName;
                }
            }

            else if (!PyObject_Compare(aspect, required_NAME))
            {
                if (flags & REQUIRED)
                    Py_RETURN_TRUE;

                Py_RETURN_FALSE;
            }

            else if (!PyObject_Compare(aspect, defaultValue_NAME))
            {
                if (flags & DEFAULT)
                {
                    Py_INCREF(self->defaultValue);
                    return self->defaultValue;
                }
            }

            else if (!PyObject_Compare(aspect, afterChange_NAME))
            {
                if (flags & AFTERCHANGE)
                {
                    Py_INCREF(self->afterChange);
                    return self->afterChange;
                }
            }

            else if (!PyObject_Compare(aspect, indexed_NAME))
            {
                if (flags & INDEXED)
                    Py_RETURN_TRUE;

                Py_RETURN_FALSE;
            }
        }
        else if (!PyObject_Compare(aspect, redirectTo_NAME))
        {
            Py_INCREF(self->redirectTo);
            return self->redirectTo;
        }

        Py_INCREF(defaultValue);
        return defaultValue;
    }
}

static int _t_attribute_invokeAfterChange(t_attribute *self, PyObject *item,
                                          PyObject *op, PyObject *name)
{
    if (self->flags & AFTERCHANGE)
    {
        int i = -1;

        while (++i < PyList_GET_SIZE(self->afterChange)) {
            PyObject *method = PyList_GET_ITEM(self->afterChange, i);
            
            if (PyObject_HasAttr((PyObject *) item->ob_type, method))
            {
                PyObject *result = PyObject_CallMethodObjArgs(item, method,
                                                              op, name, NULL);

                if (!result)
                    return -1;
                Py_DECREF(result);
            }
        }
    }

    return 0;
}

static PyObject *t_attribute_invokeAfterChange(t_attribute *self,
                                               PyObject *args)
{
    PyObject *item, *op, *name;

    if (!PyArg_ParseTuple(args, "OOO", &item, &op, &name))
        return NULL;

    if (_t_attribute_invokeAfterChange(self, item, op, name) < 0)
        return NULL;
    
    Py_RETURN_NONE;
}


/* cardinality */

static PyObject *t_attribute__getCardinality(t_attribute *self, void *data)
{
    if (!(self->flags & REDIRECT))
    {
        PyObject *value = NULL;

        switch (self->flags & CARDINALITY) {
          case SINGLE:
            value = single_NAME;
            break;
          case LIST:
            value = list_NAME;
            break;
          case DICT:
            value = dict_NAME;
            break;
          case SET:
            value = set_NAME;
            break;
          default:
            value = single_NAME;
            break;
        }

        Py_INCREF(value);
        return value;
    }

    PyErr_SetString(PyExc_AttributeError, "cardinality");
    return NULL;
}

static int t_attribute__setCardinality(t_attribute *self, t_values *values,
                                       void *data)
{
    if (!values)
        values = (t_values *) Py_None;

    if (!PyObject_TypeCheck(values, CValues))
    {
        PyErr_SetObject(PyExc_TypeError, (PyObject *) values);
        return -1;
    }
    else
    {
        PyObject *cardinality = PyDict_GetItem(values->dict, cardinality_NAME);

        self->flags &= ~CARDINALITY;
    
        if (!cardinality || !PyObject_Compare(cardinality, single_NAME))
            self->flags |= SINGLE;
        else if (!PyObject_Compare(cardinality, list_NAME))
            self->flags |= LIST;
        else if(!PyObject_Compare(cardinality, dict_NAME))
            self->flags |= DICT;
        else if (!PyObject_Compare(cardinality, set_NAME))
            self->flags |= SET;
        else
        {
            PyErr_SetObject(PyExc_ValueError, cardinality);
            return -1;
        }

        if (self->flags & REF)
            return t_attribute__setOtherName(self, values, data);

        return 0;
    }
}


/* required property */

static PyObject *t_attribute__getRequired(t_attribute *self, void *data)
{
    if (!(self->flags & REDIRECT))
    {
        if (self->flags & REQUIRED)
            Py_RETURN_TRUE;

        Py_RETURN_FALSE;    
    }

    PyErr_SetString(PyExc_AttributeError, "required");
    return NULL;
}

static int t_attribute__setRequired(t_attribute *self, PyObject *value,
                                    void *data)
{
    if (value && PyObject_IsTrue(value))
        self->flags |= REQUIRED;
    else
        self->flags &= ~REQUIRED;

    return 0;
}

/* indexed property */

static PyObject *t_attribute__getIndexed(t_attribute *self, void *data)
{
    if (!(self->flags & REDIRECT))
    {
        if (self->flags & INDEXED)
            Py_RETURN_TRUE;

        Py_RETURN_FALSE;    
    }

    PyErr_SetString(PyExc_AttributeError, "indexed");
    return NULL;
}

static int t_attribute__setIndexed(t_attribute *self, PyObject *value,
                                    void *data)
{
    if (value && PyObject_IsTrue(value))
        self->flags |= INDEXED;
    else
        self->flags &= ~INDEXED;

    return 0;
}

/* noInherit property */

static PyObject *t_attribute__getNoInherit(t_attribute *self, void *data)
{
    if (self->flags & NOINHERIT)
        Py_RETURN_TRUE;

    Py_RETURN_FALSE;
}

static int t_attribute__setNoInherit(t_attribute *self, PyObject *value,
                                     void *data)
{
    if (!value)
        value = Py_None;

    if (!PyTuple_CheckExact(value))
    {
        PyErr_SetObject(PyExc_TypeError, value);
        return -1;
    }
    else if (!PyTuple_Size(value) == 3)
    {
        PyErr_SetObject(PyExc_ValueError, value);
        return -1;
    }
    else
    {
        PyObject *t0 = PyTuple_GET_ITEM(value, 0);

        if (!PyObject_TypeCheck(t0, CValues))
        {
            PyErr_SetObject(PyExc_TypeError, t0);
            return -1;
        }
        else
        {
            t_values *values = (t_values *) t0;
            PyObject *n1 = PyTuple_GET_ITEM(value, 1);
            PyObject *n2 = PyTuple_GET_ITEM(value, 2);
            PyObject *v1 = PyDict_GetItem(values->dict, n1);
            PyObject *v2 = PyDict_GetItem(values->dict, n2);

            if (v1 == NULL || v1 == Py_None)
            {
                if (v2 == NULL || v2 == Py_None)
                    self->flags |= NOINHERIT;
            }
            else
                self->flags &= ~NOINHERIT;

            return 0;
        }
    }
}

/* defaultValue property */

static PyObject *t_attribute__getDefaultValue(t_attribute *self, void *data)
{
    if (!(self->flags & REDIRECT) && (self->flags & DEFAULT))
    {
        Py_INCREF(self->defaultValue);
        return self->defaultValue;
    }
            
    PyErr_SetObject(PyExc_AttributeError, defaultValue_NAME);
    return NULL;
}

static int t_attribute__setDefaultValue(t_attribute *self, t_values *values,
                                        void *data)
{
    if (!values)
        values = (t_values *) Py_None;

    if (!PyObject_TypeCheck(values, CValues))
    {
        PyErr_SetObject(PyExc_TypeError, (PyObject *) values);
        return -1;
    }
    else
    {
        PyObject *defaultValue =
            PyDict_GetItem(values->dict, defaultValue_NAME);

        if (defaultValue == NULL)
        {
            self->flags &= ~DEFAULT;
            Py_XDECREF(self->defaultValue);
            self->defaultValue = NULL;
        }
        else
        {
            self->flags |= DEFAULT;
            Py_INCREF(defaultValue);
            self->defaultValue = defaultValue;
        }

        return 0;
    }
}

/* afterChange property */

static PyObject *t_attribute__getAfterChange(t_attribute *self, void *data)
{
    if (!(self->flags & REDIRECT) && (self->flags & AFTERCHANGE))
    {
        Py_INCREF(self->afterChange);
        return self->afterChange;
    }
            
    PyErr_SetObject(PyExc_AttributeError, afterChange_NAME);
    return NULL;
}

static int t_attribute__setAfterChange(t_attribute *self, t_values *values,
                                       void *data)
{
    if (!values)
        values = (t_values *) Py_None;

    if (!PyObject_TypeCheck(values, CValues))
    {
        PyErr_SetObject(PyExc_TypeError, (PyObject *) values);
        return -1;
    }
    else
    {
        PyObject *afterChange = PyDict_GetItem(values->dict, afterChange_NAME);

        if (afterChange == NULL)
        {
            self->flags &= ~AFTERCHANGE;
            Py_XDECREF(self->afterChange);
            self->afterChange = NULL;
        }
        else if (PyList_Check(afterChange))
        {
            self->flags |= AFTERCHANGE;
            Py_INCREF(afterChange);
            self->afterChange = afterChange;
        }
        else
        {
            PyErr_SetObject(PyExc_TypeError, (PyObject *) afterChange);
            return -1;
        }

        return 0;
    }
}

/* redirectTo property */

static PyObject *t_attribute__getRedirectTo(t_attribute *self, void *data)
{
    PyObject *value;

    if (self->flags & REDIRECT)
        value = self->redirectTo;
    else
        value = Py_None;

    Py_INCREF(value);
    return value;
}

static int t_attribute__setRedirectTo(t_attribute *self, PyObject *value,
                                      void *data)
{
    if (!value)
    {
        PyErr_SetObject(PyExc_ValueError, Py_None);
        return -1;
    }
    
    if (t_attribute__setNoInherit(self, value, data))
        return -1;
    else
    {
        t_values *values = (t_values *) PyTuple_GET_ITEM(value, 0);
        PyObject *redirectTo = PyDict_GetItem(values->dict, redirectTo_NAME);

        if (redirectTo)
            Py_INCREF(redirectTo);
        Py_XDECREF(self->redirectTo);
        self->redirectTo = redirectTo;

        self->flags &= ~ATTRDICT;
        if (redirectTo == NULL || redirectTo == Py_None)
        {
            self->flags &= ~(REDIRECT | PROCESS);
            return t_attribute__setOtherName(self, values, data);
        }
        else
        {
            self->flags |= REDIRECT | PROCESS;
            return 0;
        }
    }
}

/* otherName property */

static PyObject *t_attribute__getOtherName(t_attribute *self, void *data)
{
    if (!(self->flags & REDIRECT))
    {
        PyObject *value;

        if (self->flags & REF)
            value = self->otherName;
        else
            value = Py_None;

        Py_INCREF(value);
        return value;
    }

    PyErr_SetString(PyExc_AttributeError, "otherName");
    return NULL;
}

static int t_attribute__setOtherName(t_attribute *self, t_values *values,
                                     void *data)
{
    if (!values)
        values = (t_values *) Py_None;

    if (!PyObject_TypeCheck(values, CValues))
    {
        PyErr_SetObject(PyExc_TypeError, (PyObject *) values);
        return -1;
    }
    else
    {
        PyObject *otherName = PyDict_GetItem(values->dict, otherName_NAME);

        if (otherName)
            Py_INCREF(otherName);
        Py_XDECREF(self->otherName);
        self->otherName = otherName;

        self->flags &= ~ATTRDICT;
        if (otherName == NULL || otherName == Py_None)
        {
            t_item *item = values->ref->item;
            t_values *references = item->references;

            return t_attribute__setTypeID(self, references, data);
        }
        else
        {
            self->flags |= REF;

            if (self->flags & SINGLE)
                self->flags |= PROCESS;
            else if (self->flags & LIST)
                self->flags &= ~PROCESS;

            return 0;
        }
    }
}

/* typeID property */

static PyObject *t_attribute__getTypeID(t_attribute *self, void *data)
{
    if (!(self->flags & (REDIRECT | REF)))
    {
        PyObject *value;

        if (self->flags & VALUE)
        {
            if (self->typeID == NULL)
                value = Py_None;
            else
                value = self->typeID;
        }
        else
            value = Py_None;

        Py_INCREF(value);
        return value;
    }

    PyErr_SetString(PyExc_AttributeError, "typeID");
    return NULL;
}

static int t_attribute__setTypeID(t_attribute *self, t_values *refs, void *data)
{
    if (!(self->flags & (REDIRECT | REF)))
    {
        if (!refs)
            refs = (t_values *) Py_None;

        if (!PyObject_TypeCheck(refs, CValues))
        {
            PyErr_SetObject(PyExc_TypeError, (PyObject *) refs);
            return -1;
        }
        else if (PyDict_Contains(refs->dict, type_NAME))
        {
            PyObject *type =
                PyObject_CallMethodObjArgs((PyObject *) refs, _getRef_NAME,
                                           type_NAME, Py_None, Py_None, NULL);

            if (!type)
                return -1;

            if (type == Py_None)
            {
                Py_DECREF(type);
                self->flags |= PROCESS;
                Py_XDECREF(self->typeID);
                self->typeID = NULL;
            }
            else
            {
                PyObject *typeFlags =
                    PyObject_CallMethodObjArgs(type, getFlags_NAME, NULL);

                if (!typeFlags)
                {
                    Py_DECREF(type);
                    return -1;
                }

                if (!PyInt_Check(typeFlags))
                {
                    PyErr_SetObject(PyExc_TypeError, typeFlags);
                    Py_DECREF(type);
                    Py_DECREF(typeFlags);

                    return -1;
                }

                self->flags &= ~PROCESS;
                self->flags |= PyInt_AsLong(typeFlags);
                Py_DECREF(typeFlags);

                Py_INCREF(((t_item *) type)->ref->uuid);
                Py_XDECREF(self->typeID);
                self->typeID = ((t_item *) type)->ref->uuid;
                Py_DECREF(type);
            }
        }
        else
        {
            self->flags |= PROCESS;
            Py_XDECREF(self->typeID);
            self->typeID = NULL;
        }
        
        self->flags |= VALUE;
    }

    return 0;
}

/* process property */

static PyObject *t_attribute__getProcess(t_attribute *self, void *data)
{
    return PyInt_FromLong(self->flags & PROCESS);
}


void _init_attribute(PyObject *m)
{
    if (PyType_Ready(&AttributeType) >= 0)
    {
        if (m)
        {
            PyObject *dict, *cobj;

            Py_INCREF(&AttributeType);
            PyModule_AddObject(m, "CAttribute", (PyObject *) &AttributeType);

            CAttribute = &AttributeType;

            dict = AttributeType.tp_dict;
            PyDict_SetItemString_Int(dict, "VALUE", VALUE);
            PyDict_SetItemString_Int(dict, "REF", REF);
            PyDict_SetItemString_Int(dict, "REDIRECT", REDIRECT);
            PyDict_SetItemString_Int(dict, "REQUIRED", REQUIRED);
            PyDict_SetItemString_Int(dict, "INDEXED", INDEXED);
            PyDict_SetItemString_Int(dict, "PROCESS_GET", PROCESS_GET);
            PyDict_SetItemString_Int(dict, "PROCESS_SET", PROCESS_SET);
            PyDict_SetItemString_Int(dict, "SINGLE", SINGLE);
            PyDict_SetItemString_Int(dict, "LIST", LIST);
            PyDict_SetItemString_Int(dict, "DICT", DICT);
            PyDict_SetItemString_Int(dict, "SET", SET);
            PyDict_SetItemString_Int(dict, "ALIAS", ALIAS);
            PyDict_SetItemString_Int(dict, "KIND", KIND);
            PyDict_SetItemString_Int(dict, "NOINHERIT", NOINHERIT);
            PyDict_SetItemString_Int(dict, "SIMPLE", SIMPLE);
            PyDict_SetItemString_Int(dict, "DEFAULT", DEFAULT);
            PyDict_SetItemString_Int(dict, "PROCESS", PROCESS);
            PyDict_SetItemString_Int(dict, "CARDINALITY", CARDINALITY);
            PyDict_SetItemString_Int(dict, "ATTRDICT", ATTRDICT);

            _getRef_NAME = PyString_FromString("_getRef");
            getFlags_NAME = PyString_FromString("getFlags");
            cardinality_NAME = PyString_FromString("cardinality");
            single_NAME = PyString_FromString("single");
            list_NAME = PyString_FromString("list");
            dict_NAME = PyString_FromString("dict");
            set_NAME = PyString_FromString("set");
            required_NAME = PyString_FromString("required");
            indexed_NAME = PyString_FromString("indexed");
            otherName_NAME = PyString_FromString("otherName");
            redirectTo_NAME = PyString_FromString("redirectTo");
            inheritFrom_NAME = PyString_FromString("inheritFrom");
            defaultValue_NAME = PyString_FromString("defaultValue");
            type_NAME = PyString_FromString("type");
            afterChange_NAME = PyString_FromString("afterChange");

            cobj = PyCObject_FromVoidPtr(_t_attribute_invokeAfterChange, NULL);
            PyModule_AddObject(m, "CAttribute_invokeAfterChange", cobj);
        }
    }
}
