# FUZZSDN
## Learning Failure-Inducing Models for Testing Software-Defined Networks


This repository contains the artifacts of our paper, entitled "Learning Failure-Inducing Models for Testing Software-Defined Networks".

### Overview:

Software-defined networks (SDN) enable flexible and effective communication systems that are managed by centralized
software controllers. However, such a controller can undermine the underlying communication network of an SDN-based
system and thus must be carefully tested. When an SDN-based system fails, in order to address such a failure, engineers
need to precisely understand the conditions under which it occurs. In this article, we introduce a machine
learning-guided fuzzing method, named FuzzSDN, aiming at both (1) generating effective test data leading to failures in
SDN-based systems and (2) learning accurate failure-inducing models that characterize conditions under which such system
fails. To our knowledge, no existing work simultaneously addresses these two objectives for SDNs. We evaluate FuzzSDN by
applying it to systems controlled by two open-source SDN controllers. Further, we compare FuzzSDN with two
state-of-the-art methods for fuzzing SDNs and two baselines for learning failure-inducing models.
Our results show that (1) compared to the state-of-the-art methods, FuzzSDN generates at least 12 times more failures,
within the same time budget, with a controller that is fairly robust to fuzzing and (2) our failure-inducing models
have, on average, a precision of 98% and a recall of 86%, significantly outperforming the baselines.


### Prerequisites
#### Virtual Machine:
OS: Ubuntu 16.04+ |
CPU: 4 Cores |
Memory: 10GB |
Disk Space: 50GB

Mininet: http://mininet.org/ |
Version: 2.3.0 |
Installation: http://mininet.org/download/


ONOS: https://onosproject.org/ |
Version: 2.6.0 |
Installation: https://wiki.onosproject.org/display/ONOS/Getting+the+ONOS+core+source+code+using+git+and+Gerrit

RYU: https://ryu-sdn.org |
Version: 4.34 |
Installation: https://ryu-sdn.org


### How to perform experiments ?
Step 0: Exctract fuzzsdn.zip to any PATH\
Step 1: Move to PATH\
Step 2: Move to "./bin" and run "./pre-install.sh"\
Step 3: Move to PATH and run "pip install --editable ."\
Step 4: Run the command "screen"\
Step 5: Run the command "fuzzsdn experiment run".\
Step 6: Detach the screen using the keyboard shortcut "Ctrl+A+D"\
Step 7: Once the experiment is completed, run "fuzzsdn experiment report " to obtain the results
