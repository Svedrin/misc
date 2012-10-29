/* ======== spawnhealth_mm ========
* Copyright (C) 2004-2005 TonyAngione
* No warranties of any kind
*
* License: freeware
*
* Author(s): Tony Angione
* =================================
*/

#include "cvars.h"
#include "warrior_mm.h"

SampleAccessor g_Accessor;

bool SampleAccessor::RegisterConCommandBase(ConCommandBase *pVar)
{
	//this will work on any type of concmd!
	return META_REGCVAR(pVar);
}
