/* ======== spawnhealth_mm ========
* Copyright (C) 2004-2005 TonyAngione
* No warranties of any kind
*
* License: freeware
*
* Author(s): Tony Angione
* =================================
*/

#ifndef _INCLUDE_CVARS_H
#define _INCLUDE_CVARS_H

#include <convar.h>

class SampleAccessor : public IConCommandBaseAccessor
{
public:
	virtual bool RegisterConCommandBase(ConCommandBase *pVar);
};

extern SampleAccessor g_Accessor;

#endif //_INCLUDE_CVARS_H
