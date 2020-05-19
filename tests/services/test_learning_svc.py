import pytest
from app.objects.c_adversary import Adversary
from app.objects.secondclass.c_fact import Fact
from app.utility.base_world import BaseWorld


@pytest.fixture
def setup_learning_service(loop, data_svc, ability, operation, link):
    tability = ability(tactic='discovery', technique_id='T1033', technique='Find', name='test',
                       test='d2hvYW1pCg==', description='find active user', cleanup='', executor='sh',
                       platform='darwin', payloads=['wifi.sh'], parsers=[], requirements=[], privilege=None,
                       variations=[])
    loop.run_until_complete(data_svc.store(tability))
    toperation = operation(name='sample', agents=None, adversary=Adversary(name='sample', adversary_id='XYZ',
                                                                           atomic_ordering=[], description='test'))
    loop.run_until_complete(data_svc.store(toperation))
    tlink = link(ability=tability, command='', paw='')
    yield toperation, tlink


class TestLearningSvc:

    def test_learn(self, loop, setup_learning_service, learning_svc):
        operation, link = setup_learning_service
        operation.add_link(link)
        loop.run_until_complete(learning_svc.learn(
            facts=operation.all_facts(),
            link=link,
            blob=BaseWorld.encode_string('i contain 1 ip address 192.168.0.1 and one file /etc/host.txt. that is all.'))
        )
        assert len(link.facts) == 2

    def test_build_relationships(self, loop, setup_learning_service, learning_svc):
        _, link = setup_learning_service
        learning_svc.model.add(frozenset({'host.user.name', 'target.org.name'}))
        learning_svc.model.add(frozenset({'host.file.extension', 'host.user.name', 'domain.user.name'}))
        facts = [
            Fact(trait='target.org.name', value='something'),
            Fact(trait='host.user.name', value='admin'),
            Fact(trait='host.user.name', value='root'),
            Fact(trait='domain.user.name', value='user'),
            Fact(trait='not.really.here', value='should never be found')
        ]
        loop.run_until_complete(learning_svc._build_relationships(link, facts))
        assert len(link.relationships) == 4
