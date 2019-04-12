# Copyright 2019 The Cirq Developers
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Sampling/simulation methods that delegate to appropriate simulators."""

from typing import List, Optional, Type, Union

import numpy as np

from cirq import circuits, protocols, study, schedules, ops, line
from cirq.sim import sparse_simulator, density_matrix_simulator


def sample(program: Union[circuits.Circuit, schedules.Schedule],
           *,
           param_resolver: Optional[study.ParamResolver] = None,
           repetitions: int = 1,
           dtype: Type[np.number] = np.complex64) -> study.TrialResult:
    """Simulates sampling from the given circuit or schedule.

    Args:
        program: The circuit or schedule to sample from.
        param_resolver: Parameters to run with the program.
        repetitions: The number of samples to take.
        dtype: The `numpy.dtype` used by the simulation. Typically one of
            `numpy.complex64` or `numpy.complex128`.
            Favors speed over precision by default, i.e. uses `numpy.complex64`.
    """

    # State vector simulation is much faster, but only works if no randomness.
    if protocols.has_unitary(program):
        return sparse_simulator.Simulator(dtype=dtype).run(
            program=program,
            param_resolver=param_resolver,
            repetitions=repetitions)

    return density_matrix_simulator.DensityMatrixSimulator(
        dtype=dtype).run(
            program=program,
            param_resolver=param_resolver,
            repetitions=repetitions)


def out_vector(program: Union[ops.Operation, ops.Gate, circuits.Circuit, schedules.Schedule],
               *,
               initial_state: Union[int, np.ndarray] = 0,
               param_resolver: Optional[study.ParamResolver] = None,
               qubit_order: ops.QubitOrderOrList = ops.QubitOrder.DEFAULT,
               dtype: Type[np.number] = np.complex64
               ) -> 'np.ndarray':
    """Returns the wavefunction resulting from applying an object.

    Args:
        program: The circuit, schedule, gate, or operation to apply to the
            initial state in order to produce the result.
        param_resolver: Parameters to run with the program.
        qubit_order: Determines the canonical ordering of the qubits. This
            is often used in specifying the initial state, i.e. the
            ordering of the computational basis states.
        initial_state: If an int, the state is set to the computational
            basis state corresponding to this state. Otherwise  if this
            is a np.ndarray it is the full initial state. In this case it
            must be the correct size, be normalized (an L2 norm of 1), and
            be safely castable to an appropriate dtype for the simulator.
        dtype: The `numpy.dtype` used by the simulation. Typically one of
            `numpy.complex64` or `numpy.complex128`.
            Favors speed over precision by default, i.e. uses `numpy.complex64`.
    """

    if not protocols.has_unitary(program):
        raise ValueError(
            "Given object is not unitary. "
            "Non-unitary operations don't have "
            "a single well defined output state vector. "
            "Maybe you wanted `cirq.sample_wavefunction`?")

    if isinstance(program, ops.Gate):
        program = circuits.Circuit.from_ops(program.on(
            *line.LineQubit.range(program.num_qubits())))
    elif isinstance(program, ops.Operation):
        program = circuits.Circuit.from_ops(program)

    return sparse_simulator.Simulator(dtype=dtype).simulate(
        program=program,
        initial_state=initial_state,
        qubit_order=qubit_order,
        param_resolver=param_resolver
    ).state_vector()


def sample_sweep(program: Union[circuits.Circuit, schedules.Schedule],
                 params: study.Sweepable,
                 *,
                 repetitions: int = 1,
                 dtype: Type[np.number] = np.complex64
                 ) -> List[study.TrialResult]:
    """Runs the supplied Circuit or Schedule, mimicking quantum hardware.

    In contrast to run, this allows for sweeping over different parameter
    values.

    Args:
        program: The circuit or schedule to simulate.
        params: Parameters to run with the program.
        repetitions: The number of repetitions to simulate, per set of
            parameter values.
        dtype: The `numpy.dtype` used by the simulation. Typically one of
            `numpy.complex64` or `numpy.complex128`.
            Favors speed over precision by default, i.e. uses `numpy.complex64`.

    Returns:
        TrialResult list for this run; one for each possible parameter
        resolver.
    """
    circuit = (program if isinstance(program, circuits.Circuit)
               else program.to_circuit())
    param_resolvers = study.to_resolvers(params)

    trial_results = []  # type: List[study.TrialResult]
    for param_resolver in param_resolvers:
        measurements = sample(circuit,
                              param_resolver=param_resolver,
                              repetitions=repetitions,
                              dtype=dtype)
        trial_results.append(measurements)
    return trial_results
