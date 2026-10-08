# RAG and the deep-analysis example

The user asked to implement missing RAG according to BaixueWu_Research_Proposal.pdf and find an online review with a film that can be edited publicly. The root PDF is byte-identical to the existing dev/materials copy and was not added again.

DG3 requires external grounding, and DG4 keeps the creator in charge. The existing analysis style changed writing/pacing but the image-search fallback silently returned nothing with the default backend. The shared source, retrieval and approval layer addresses that gap.

The user explicitly confirmed: “这轮也要加入外部图片检索与插入”. This scope is implemented alongside text RAG: Commons search, reviewed approval, timeline insertion, revocation and export credits. Multimodal coverage-gap scoring and semantic text retrieval remain future work.

Research candidate: Jeffrey Vance's Sherlock Jr. essay hosted by the US Library of Congress gives strong formal-analysis material, but the Commons film's public-domain notice is jurisdiction-specific. Sintel was selected for the public study because its official CC BY 3.0 license explicitly permits adaptation. Shashwat Pant's review gives a traceable critical starting point; the study distinguishes it from independently observed frames.

The old local sintel-analysis draft contains unsupported plot details and was not republished. The new study uses separately checked stills at 03:16, 10:10 and 11:09 in the existing official 720p MKV. It is not a finished new commentary video or a full temporal/affective coverage implementation.

The user then clarified that the requested deep-analysis example is a complete film-analysis video. The prior study page and short image test did not satisfy that deliverable. A finished Chinese Sintel commentary now becomes the primary output; the evidence page supports the video. See dev/examples/sintel-analysis/plan.json for the narration and editorial ranges.
