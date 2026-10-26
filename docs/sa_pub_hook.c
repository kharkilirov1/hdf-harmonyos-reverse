/* LD_PRELOAD hook: force SystemAbility::Publish for SA 401 (BMS).
 * Interposes SystemAbility::AddSystemAbilityListener(int) which BMS calls
 * during OnStart (ids 3299, 0x100500, 8250). SA id sits at offset 8 of
 * SystemAbility object (seen in Publish disasm: ldr w7,[x0,#8]).
 */
#define _GNU_SOURCE
#include <stdio.h>
#include <dlfcn.h>
#include <string.h>

struct sptr_obj { void *p; };

typedef int (*listener_fn)(void *self, int id);
typedef struct sptr_obj (*getobj_fn)(void *self);
typedef void (*publish_fn)(void *self, void *sptr_ref);

static int published = 0;

__attribute__((visibility("default")))
int _ZN4OHOS13SystemAbility24AddSystemAbilityListenerEi(void *self, int id)
{
	static listener_fn real = 0;
	if (!real)
		real = (listener_fn)dlsym(RTLD_NEXT,
			"_ZN4OHOS13SystemAbility24AddSystemAbilityListenerEi");
	int r = real ? real(self, id) : 0;

	if (!published && self) {
		int said = *(int *)((char *)self + 8);
		if (said == 401) {
			getobj_fn get = (getobj_fn)dlsym(RTLD_DEFAULT,
				"_ZN4OHOS13SystemAbility22GetAbilityRemoteObjectEv");
			publish_fn pub = (publish_fn)dlsym(RTLD_DEFAULT,
				"_ZN4OHOS13SystemAbility7PublishENS_4sptrINS_13IRemoteObjectEEE");
			fprintf(stderr, "SAHOOK: listener id=%d self=%p said=%d get=%p pub=%p\n",
				id, self, said, (void *)get, (void *)pub);
			if (get && pub) {
				struct sptr_obj o = get(self);
				fprintf(stderr, "SAHOOK: remote obj=%p, publishing...\n", o.p);
				pub(self, &o);
				published = 1;
				fprintf(stderr, "SAHOOK: publish returned\n");
			}
		}
	}
	return r;
}
