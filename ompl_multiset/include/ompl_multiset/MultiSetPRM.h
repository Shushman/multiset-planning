/* requires:
#include <string>
#include <vector>
#include <ompl/base/Planner.h>
#include <ompl_multiset/Roadmap.h>
#include <ompl_multiset/Cache.h>
*/

namespace ompl_multiset
{

class MultiSetPRM : public ompl::base::Planner
{
public:
   static MultiSetPRM * create(
      const ompl::base::StateSpacePtr space,
      const ompl_multiset::RoadmapPtr roadmap,
      const ompl_multiset::CachePtr cache);
   virtual ~MultiSetPRM(void) {};

   // ompl planner interface
   virtual void setProblemDefinition(const ompl::base::ProblemDefinitionPtr & pdef) = 0;
   virtual ompl::base::PlannerStatus solve(const ompl::base::PlannerTerminationCondition & ptc) = 0;
   virtual void clear(void) = 0;
   
   // PRM parameters
   virtual void set_interroot_radius(double interroot_radius) = 0;
   virtual void set_lambda(double lambda) = 0;
   
   virtual void set_dumpfile(const char * dumpfile) = 0;

   // this will resize our list of sis,
   // update our check model,
   // and update the check mask on all vertices/edges;
   // if setProblemDefinition is called refrerncing an unknown si,
   // this function will be called with a default cost of 1.0
   virtual void add_cfree(const ompl::base::SpaceInformationPtr si, std::string name, double check_cost) = 0;

   // add relations between cfrees
   virtual void add_inclusion(
      const ompl::base::SpaceInformationPtr si_superset,
      const ompl::base::SpaceInformationPtr si_subset) = 0;
   virtual void add_intersection(
      const ompl::base::SpaceInformationPtr si_a,
      const ompl::base::SpaceInformationPtr si_b,
      const ompl::base::SpaceInformationPtr si_intersection) = 0;
   
   // extras
   virtual void force_batch() = 0;
   virtual void force_eval_everything() = 0; // just for the current problem definition!
   
   // load the roadmap and any si's from the cache
   virtual void cache_load() = 0;
   virtual void cache_save() = 0;

protected:
   MultiSetPRM(const ompl::base::SpaceInformationPtr & si, const std::string & name):
      ompl::base::Planner(si,name) {}
};

} // namespace ompl_multiset_prm
