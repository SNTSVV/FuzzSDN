## [0.7.0](https://gitlab.uni.lu/rollando/feedback_loop_experiment/compare/0.6.0...0.7.0) (2022-06-14)


### ⚠ BREAKING CHANGES

* complete change of cli API
* moved all files from figsdn_report package inside the figsdn package
* moved all files from common package inside the figsdn package
* moved all files from figsdn package to an app subpackage

### Features

* QOL improvement before version bump ([9ca84fd](https://gitlab.uni.lu/rollando/feedback_loop_experiment/commit/9ca84fdef7a674cb954f1d4ca947b5787ab7115f))


### Code Refactoring

* merge executable of figsdn and figsdn-report ([5a711bb](https://gitlab.uni.lu/rollando/feedback_loop_experiment/commit/5a711bb01afcb40b7c414e9164ceadfcce2596da))
* move all files from common package inside the figsdn package ([3d9c7ea](https://gitlab.uni.lu/rollando/feedback_loop_experiment/commit/3d9c7ea78888853a26d1736b880921c97d57473c))
* move all files from figsdn package to an app subpackage ([59796b0](https://gitlab.uni.lu/rollando/feedback_loop_experiment/commit/59796b0fae9d139fc50ad1e58348ae39fb8f2cea))
* move all files from figsdn_report package inside the figsdn package ([3c50604](https://gitlab.uni.lu/rollando/feedback_loop_experiment/commit/3c5060493de568840faeec6bc238bb5988545311))

## [0.6.0](https://gitlab.uni.lu/rollando/feedback_loop_experiment/compare/0.5.0...0.6.0) (2022-06-09)


### Features

* add argument to choose budget calculation method ([c7cd7d3](https://gitlab.uni.lu/rollando/feedback_loop_experiment/commit/c7cd7d3768646fa3c15cb14a63288d79d7a9b50a))
* add generation of a result csv file ([5543c1b](https://gitlab.uni.lu/rollando/feedback_loop_experiment/commit/5543c1bf7438e11772f0d495b41b855046ad2e66))
* introduce new budget calculation method ([a855605](https://gitlab.uni.lu/rollando/feedback_loop_experiment/commit/a8556052910a0bbec4af3b20a8c29d707e12b0e8))

## [0.5.0](https://gitlab.uni.lu/rollando/feedback_loop_experiment/compare/0.4.1...0.5.0) (2022-06-01)


### Features

* add new arguments and features to figsdn-report ([2f025ec](https://gitlab.uni.lu/rollando/feedback_loop_experiment/commit/2f025eceabfa070c3d518285d3a48825012682b8))

### [0.4.1](https://gitlab.uni.lu/rollando/feedback_loop_experiment/compare/0.4.0...0.4.1) (2022-05-31)


### Bug Fixes

* fix display and computing of confusion matrices ([f3214df](https://gitlab.uni.lu/rollando/feedback_loop_experiment/commit/f3214dffe44687855a5dd4229d85d489d04a49d4))
* fix issue were the saving of FP and TP were swapped ([beac0b6](https://gitlab.uni.lu/rollando/feedback_loop_experiment/commit/beac0b69d3d606779ae6629bcebe96eb598fc9ad))
* solve argument -F/--filter that couldn't be left empty ([368c2be](https://gitlab.uni.lu/rollando/feedback_loop_experiment/commit/368c2bee5250027d728e2d14e02a606f84b550f8))

## [0.4.0](https://gitlab.uni.lu/rollando/feedback_loop_experiment/compare/0.3.0...0.4.0) (2022-05-27)


### ⚠ BREAKING CHANGES

* ~ Rename cli args "ml_algorithm" to "algorithm" and "preprocessing-strategy" to "filter"

### Features

* Add new metrics to measure dataset quality ([d599b72](https://gitlab.uni.lu/rollando/feedback_loop_experiment/commit/d599b72563a85784ff7b29ec02837a05508ea4ee))
* add simple strategy to reproduce BEADS baseline ([83f879c](https://gitlab.uni.lu/rollando/feedback_loop_experiment/commit/83f879c72ded4ca68e5305e09f7eb65a8dd558e7))
* add storage of classifier scheme ([361c2ec](https://gitlab.uni.lu/rollando/feedback_loop_experiment/commit/361c2ecb7a5b31c7b5b8548a1104a2691411266a))


### Bug Fixes

* add missing files from commit '7ddb06b2' ([c40b879](https://gitlab.uni.lu/rollando/feedback_loop_experiment/commit/c40b879fcf1cf47fd1027a204e3c857129872c8d))
* fix an issue where the filter hyperparameters were ignored. ([cd3204d](https://gitlab.uni.lu/rollando/feedback_loop_experiment/commit/cd3204d18970ccc1c8bbe97b7dc31ae8fb13df8d))
* fix some artifacts that caused issues in some cases ([3c251aa](https://gitlab.uni.lu/rollando/feedback_loop_experiment/commit/3c251aaa38112d9a4ce43195f72e3ed15243f2ab))
* rename module "lib" into "common" ([3ecb382](https://gitlab.uni.lu/rollando/feedback_loop_experiment/commit/3ecb38230544d93d5fdb705995610c27a3829204))


* !style: update some variables names ([fd5bd57](https://gitlab.uni.lu/rollando/feedback_loop_experiment/commit/fd5bd57b8e6562591879b2fb7c3bb50a079246f1))

## [0.2.0](https://gitlab.uni.lu/rollando/feedback_loop_experiment/compare/0.1.0...0.2.0) (2022-03-24)


### ⚠ BREAKING CHANGES

* allow printing of a debug report
* Having root permissions is no longer required, however, a sudo password should be created, password-less sudo permissions given to the user or sudo password being given at the beginning of the script

### Features

* add editable config file ([6c0b138](https://gitlab.uni.lu/rollando/feedback_loop_experiment/commit/6c0b138faf45b6803b040767562fb2ccfa612cd9))
* add hyper-parameters support for pre-processing strategies ([161d77a](https://gitlab.uni.lu/rollando/feedback_loop_experiment/commit/161d77afee46f4b08efe35b0ce414e1f8ecc13d3))
* add installation script ([83f441d](https://gitlab.uni.lu/rollando/feedback_loop_experiment/commit/83f441da4af9997e79c7dccbd405c3d1f895b28b))
* add mininet driver ([9446f10](https://gitlab.uni.lu/rollando/feedback_loop_experiment/commit/9446f106f659a9bf75be0a4c6b7860809d4657ca))
* add mode selection and hyper-parameters support ([aa0e60a](https://gitlab.uni.lu/rollando/feedback_loop_experiment/commit/aa0e60a9bbc1e367aea3d34e450f617d7e8eb64c))
* add new command line arguments ([67e8078](https://gitlab.uni.lu/rollando/feedback_loop_experiment/commit/67e807858ebf903be33c98917644a6f3e2e35ed2))
* Add parameters for mutation rate and bump version number ([b56ed10](https://gitlab.uni.lu/rollando/feedback_loop_experiment/commit/b56ed1017d4021a4dcacfcd6db508e7a8475984d))
* Add possibility to use different data formatting methods ([7faeca7](https://gitlab.uni.lu/rollando/feedback_loop_experiment/commit/7faeca776a7638b54fe2c04a794c480a83a441aa))
* Add support for custom rule ([fcad1b4](https://gitlab.uni.lu/rollando/feedback_loop_experiment/commit/fcad1b45963495ea578fd6b17a3ffec26adad739))
* Add support for extra information in fuzzed messages ([e977279](https://gitlab.uni.lu/rollando/feedback_loop_experiment/commit/e977279640cabfeccc3bd680318a6e9c051e901b))
* add support for RYU SDN Controller ([026e23f](https://gitlab.uni.lu/rollando/feedback_loop_experiment/commit/026e23fbf436530fb02483610df16e3d52f9657f))
* allow printing of a debug report ([3710dca](https://gitlab.uni.lu/rollando/feedback_loop_experiment/commit/3710dca9d7a47c5a8f24df4056de11d41c2dad24))
* Change rule mechanism ([aaab626](https://gitlab.uni.lu/rollando/feedback_loop_experiment/commit/aaab626df302d8aebd5644c5eb894cd18154970d))
* Makes the experiment installable ([6d8ba00](https://gitlab.uni.lu/rollando/feedback_loop_experiment/commit/6d8ba00886f9ffda70ca5c1d6a70baf946cde97d))
* update algorithm ([833dd1c](https://gitlab.uni.lu/rollando/feedback_loop_experiment/commit/833dd1cfc83486b94ba03683505b7ff29387aed8))


### Bug Fixes

* allow iteration to continue even if there is no rules. ([6cbe8a0](https://gitlab.uni.lu/rollando/feedback_loop_experiment/commit/6cbe8a05d1fd2b747a2df26dd1e6643e3b4fcc17))
* fix an error introduced by previous commit ([51d5b4c](https://gitlab.uni.lu/rollando/feedback_loop_experiment/commit/51d5b4cfa1605cceee0868442e955829704faec7))
* fix bash related warnings ([ff509bb](https://gitlab.uni.lu/rollando/feedback_loop_experiment/commit/ff509bb41a52411332a98b69b7cf15b49164876b))
* Fix budget rounding issue ([8b35c8c](https://gitlab.uni.lu/rollando/feedback_loop_experiment/commit/8b35c8cd23391c5f89e98aecf6fe045add4e7dbf))
* Fix cli command orthography ([c22bbd7](https://gitlab.uni.lu/rollando/feedback_loop_experiment/commit/c22bbd7aac5204c049ceff2eefe26a765d1373f3))
* Fix error that prevented the algorithm to converge ([c68e160](https://gitlab.uni.lu/rollando/feedback_loop_experiment/commit/c68e1600c1c77a9523845aeaad6aa644a04276b5))
* Fix mutation rate not being update when using command lines ([d2bec06](https://gitlab.uni.lu/rollando/feedback_loop_experiment/commit/d2bec06d497d8da5d940f3362e4360ecd4277809))
* perform two fixes ([665f2af](https://gitlab.uni.lu/rollando/feedback_loop_experiment/commit/665f2af66da1d146a5b8834e33baed70c72514c3))


### Code Refactoring

* remove need for having admin permissions ([cf94474](https://gitlab.uni.lu/rollando/feedback_loop_experiment/commit/cf944743a7db03eb0353aafbacdc3bba8f83e092))

## [0.1.0](https://gitlab.uni.lu/rollando/feedback_loop_experiment/compare/9658920c901086449693f92457bb036f8b42a7b1...0.1.0) (2021-07-07)


### Features

* Import first version of the experiment ([9658920](https://gitlab.uni.lu/rollando/feedback_loop_experiment/commit/9658920c901086449693f92457bb036f8b42a7b1))

