# @ray.remote
# def gather_and_wait(args):
#     return ray.get(args)
#
#
# # used to pipe dag nodes which outputs do not depend on each other
# @ray.remote
# def chain_no_ret(*args):
#     return args[0]
#
#
# @ray.remote
# def write_batch(db_actor: DbActor, batch: List[DataCatalog]) -> Dict:
#     return ray.get(db_actor.write_batch.remote(batch))
#
#
# @ray.remote
# def filter_existing(db_actor: DbActor, input_batch: InputItemBatch) -> InputItemBatch:
#     return ray.get(db_actor.filter_batch.remote(input_batch))

